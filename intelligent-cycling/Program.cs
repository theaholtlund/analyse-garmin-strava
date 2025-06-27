using System;
using System.IO;
using DotNetEnv;
using IntelligentCycling.ApiConnector; // Ensure this package is compatible or replace with your own logic

class Program {
    static void Main(string[] args) {
        // Load .env file with credentials
        Env.Load();
        string user = Environment.GetEnvironmentVariable("IC_USER");
        string pass = Environment.GetEnvironmentVariable("IC_PASS");

        if (string.IsNullOrEmpty(user) || string.IsNullOrEmpty(pass)) {
            Console.Error.WriteLine("ERROR: IC_USER or IC_PASS not set in .env");
            return;
        }

        var client = new ICClient(user, pass); // You may need to implement this if the package doesn't work
        var activities = client.GetNewActivities();

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
