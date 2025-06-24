using System;
using System.IO;
using IntelligentCycling.ApiConnector;

class Program {
    static void Main(string[] args) {
        string user = Environment.GetEnvironmentVariable("IC_USER");
        string pass = Environment.GetEnvironmentVariable("IC_PASS");
        if (user == null || pass == null) {
            Console.Error.WriteLine("ERROR: Set IC_USER and IC_PASS");
            return;
        }
        var client = new ICClient(user, pass);
        var activities = client.GetNewActivities(); // henter nye aktiviteter
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
