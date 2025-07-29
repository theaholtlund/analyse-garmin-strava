using Garmin.Connect;
using Garmin.Connect.Auth;
using Garmin.Connect.Models;
using System;
using System.IO;
using System.Net.Http;
using System.Threading;
using System.Threading.Tasks;

class Program
{
    static async Task Main(string[] args)
    {
        // Load environment variables
        DotNetEnv.Env.Load();

        // Retrieve credentials from environment variables
        string? gcUser = Environment.GetEnvironmentVariable("GARMIN_USER");
        string? gcPass = Environment.GetEnvironmentVariable("GARMIN_PASS");

        // Validate credentials
        if (gcUser == null || gcPass == null)
        {
            Console.Error.WriteLine("ERROR: GARMIN_USER or GARMIN_PASS not set in .env");
            return;
        }

        // Initialise the HttpClient
        var httpClient = new HttpClient();

        // Authenticate and get the GarminConnectClient
        var authParameters = new BasicAuthParameters(gcUser, gcPass);
        var client = new GarminConnectClient(new GarminConnectContext(httpClient, authParameters));

        // Retrieve new activities
        int start = 0;
        int limit = 100;
        var activities = await client.GetActivities(start, limit, CancellationToken.None);

        // Set output directory
        string outDir = args.Length > 0 ? args[0] : "./activities";
        Directory.CreateDirectory(outDir);

        // Download activities
        foreach (var act in activities)
        {
            string path = Path.Combine(outDir, $"{act.ActivityId}.fit");
            if (!File.Exists(path))
            {
                client.DownloadActivity(act.ActivityId, path);
                Console.WriteLine($"Downloaded: {path}");
            }
        }
    }
}
