# Import required libraries
import datetime
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Import shared configuration and functions from other scripts
from config import logger, check_garmin_credentials, RUNNING_THROUGH_GITHUB
from garmin_connect import fetch_data, prepare_dataframe
from utils import ensure_dir

# Ensure outputs directory exists
PLOTS_DIR = "outputs"
ensure_dir(PLOTS_DIR)

# Orange colour palette
ORANGE_PALETTE = ["#FF8C42", "#FF6700", "#FF9505", "#FFA347", "#FFB366", "#FFC680", "#FFD699"]

sns.set_style("whitegrid")
plt.rcParams.update({'figure.facecolor': 'white'})


def extract_multisport_running(df):
    """Extract running distances from multisport activities and assign to correct month."""
    if df.empty:
        return pd.DataFrame()

    df = prepare_dataframe(df)
    df_multisport = df[df['activityTypeKey'] == 'multisport'].copy()
    running_records = []

    for _, row in df_multisport.iterrows():
        running_distance = 0
        laps = row.get('laps', [])

        # Sum distance of laps that are running
        for lap in laps:
            lap_type = lap.get('activityTypeKey') or lap.get('activityType', '').lower()
            if lap_type == 'running':
                running_distance += lap.get('distance', 0)

        if running_distance > 0:
            running_records.append({
                'startTimeLocal': row['startTimeLocal'],
                'distance': running_distance,
                'activityTypeKey': 'running'
            })

    if running_records:
        df_running_multisport = pd.DataFrame(running_records)
        df_running_multisport['distance_km'] = df_running_multisport['distance'] / 1000
        df_running_multisport['month'] = df_running_multisport['startTimeLocal'].dt.to_period('M')
        logger.info("Extracted running distances from %d multisport activities", len(df_running_multisport))
        return df_running_multisport
    else:
        return pd.DataFrame()


def filter_running_activities(df):
    """Filter all running activities including running segments from multisport."""
    if df.empty:
        logger.info("Received empty dataframe in filter_running_activities")
        return pd.DataFrame()

    df = prepare_dataframe(df)

    running_keys = [
        "running", "indoor_running", "treadmill_running", "track_running",
        "street_running", "obstacle_run", "ultra_run", "trail_running", "virtual_run"
    ]

    # Standard running activities
    df_running = df[df['activityTypeKey'].isin(running_keys)].copy()
    df_running['distance_km'] = df_running['distance'] / 1000
    df_running['month'] = df_running['startTimeLocal'].dt.to_period('M')

    # Include running from multisport
    df_multisport_running = extract_multisport_running(df)
    if not df_multisport_running.empty:
        df_running = pd.concat([df_running, df_multisport_running], ignore_index=True)

    logger.info("Filtered %d running activities (including multisport legs) out of %d total", len(df_running), len(df))
    return df_running


def generate_dashboard():
    """Fetch activities from Garmin Connect and generate running dashboard."""
    logger.info("Starting dashboard generation")
    garmin_creds = check_garmin_credentials()

    today = datetime.date.today()
    start_of_year = datetime.date(today.year, 1, 1)
    logger.info("Fetching activities from %s to %s", start_of_year, today)

    _, df_all = fetch_data(start_of_year, today, garmin_creds)
    if df_all.empty:
        logger.warning("No activities fetched from Garmin Connect")
        return
    logger.info("Fetched %d total activities", len(df_all))

    df_running = filter_running_activities(df_all)
    if df_running.empty:
        logger.warning("No running activities found for this year")
        return

    # Total km count
    total_km = df_running['distance_km'].sum()
    logger.info("Total running distance this year: %.2f km", total_km)

    # Monthly summary
    monthly_distances = df_running.groupby('month')['distance_km'].sum()
    cumulative_distances = monthly_distances.cumsum()
    type_counts = df_running['activityTypeKey'].value_counts()

    fig = plt.figure(constrained_layout=True, figsize=(14, 10))
    gs = fig.add_gridspec(3, 2)

    # Total km bar
    ax_total = fig.add_subplot(gs[0, 0])
    sns.barplot(x=["Total km run"], y=[total_km], palette=ORANGE_PALETTE[:1], ax=ax_total)
    ax_total.set_ylabel("Distance (km)")
    ax_total.set_title(f"Total running distance in {today.year}", fontsize=14)
    for p in ax_total.patches:
        ax_total.annotate(f"{p.get_height():.1f} km", (p.get_x() + p.get_width() / 2., p.get_height()),
                          ha='center', va='bottom', fontsize=12, fontweight='bold')

    ax_monthly = fig.add_subplot(gs[1, :])
    sns.barplot(x=monthly_distances.index.astype(str), y=monthly_distances.values,
                palette=ORANGE_PALETTE, ax=ax_monthly)
    ax_monthly.set_ylabel("Distance (km)")
    ax_monthly.set_xlabel("Month")
    ax_monthly.set_title("Monthly running distance", fontsize=14)
    for p in ax_monthly.patches:
        ax_monthly.annotate(f"{p.get_height():.1f}", (p.get_x() + p.get_width() / 2., p.get_height()),
                            ha='center', va='bottom', fontsize=10)
    ax_monthly.tick_params(axis='x', rotation=45)

    ax_cum = fig.add_subplot(gs[2, 0])
    sns.lineplot(x=cumulative_distances.index.astype(str), y=cumulative_distances.values,
                 marker="o", color="#FF6700", linewidth=2.5, ax=ax_cum)
    ax_cum.set_ylabel("Cumulative distance (km)")
    ax_cum.set_xlabel("Month")
    ax_cum.set_title("Cumulative distance over the year", fontsize=14)
    ax_cum.grid(True)
    ax_cum.tick_params(axis='x', rotation=45)
    for x, y in zip(cumulative_distances.index.astype(str), cumulative_distances.values):
        ax_cum.text(x, y + 5, f"{y:.1f}", ha='center', va='bottom', fontsize=10, fontweight='bold')

    ax_pie = fig.add_subplot(gs[2, 1])
    type_counts.plot.pie(ax=ax_pie, autopct='%1.1f%%', startangle=140, colors=ORANGE_PALETTE,
                         wedgeprops=dict(width=0.5, edgecolor='w'))
    ax_pie.set_ylabel("")
    ax_pie.set_title("Distribution of run types", fontsize=14)
    ax_pie.legend([k.replace("_", " ").title() for k in type_counts.index], bbox_to_anchor=(1, 0.5))

    dashboard_path = PLOTS_DIR + "/run_distance.png"
    fig.savefig(dashboard_path, dpi=150)
    plt.show()
    logger.info("Dashboard saved to %s", dashboard_path)


if __name__ == "__main__":
    if RUNNING_THROUGH_GITHUB:
        logger.warning("Dashboard not generated when running in GitHub Actions")
    else:
        generate_dashboard()
