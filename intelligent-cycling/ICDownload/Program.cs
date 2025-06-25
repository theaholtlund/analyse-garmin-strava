using System;
using System.IO;
using IntelligentCycling.ApiConnector;
using DotNetEnv;

class Program {
    static void Main(string[] args) {
        Env.Load();
        string user = Environment.GetEnvironmentVariable("IC_USER");
        string pass = Environment.GetEnvironmentVariable("IC_PASS");
        if (string.IsNullOrEmpty(user) || string.IsNullOrEmpty(pass)) {
            Console.Error.WriteLine("Error: IC_USER or IC_PASS not defined.");
            return;
        }

        var client = new ICClient(user, pass);
        var activities = client.GetNewActivities();  // Get new activities

        // Set output directory with default being "./activities"
        string outDir = args.Length > 0 ? args[0] : "./activities";
        Directory.CreateDirectory(outDir);

        foreach (var act in activities) {
            string path = Path.Combine(outDir, $"{act.Id}.fit");
            if (!File.Exists(path)) {
                client.DownloadActivity(act.Id, path);
                Console.WriteLine($"Downloaded: {path}");
            }
        }
    }
}
