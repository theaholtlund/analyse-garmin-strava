using System;
using DotNetEnv;
using IntelligentCycling.ApiConnector;
using Garmin.Connect;

class Program {
    static async System.Threading.Tasks.Task Main(string[] args) {
        Env.Load();

        string icUser = Environment.GetEnvironmentVariable("IC_USER");
        string icPass = Environment.GetEnvironmentVariable("IC_PASS");
        string garminUser = Environment.GetEnvironmentVariable("GARMIN_USER");
        string garminPass = Environment.GetEnvironmentVariable("GARMIN_PASS");

        if(string.IsNullOrEmpty(icUser)||string.IsNullOrEmpty(icPass)
           ||string.IsNullOrEmpty(garminUser)||string.IsNullOrEmpty(garminPass)) {
            Console.Error.WriteLine("Set IC_USER/IC_PASS and GARMIN_USER/GARMIN_PASS in .env");
            return;
        }

        // Intelligent Cycling
        var icClient = new ICClient(icUser, icPass);
        var icActs = icClient.GetNewActivities();
        if(icActs.Count > 0)
            Console.WriteLine($"[IC] Found activity ID: {icActs[0].Id}");
        else
            Console.WriteLine("[IC] No new activities found");

        // Garmin Connect
        var authParams = new BasicAuthParameters(garminUser, garminPass);
        var garminClient = new GarminConnectClient(new GarminConnectContext(new System.Net.Http.HttpClient(), authParams));
        var profile = await garminClient.GetUserProfileAsync();
        Console.WriteLine($"[Garmin] Connected as: {profile.DisplayName}");
    }
}
