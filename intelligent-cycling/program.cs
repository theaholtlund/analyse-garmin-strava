using System;
using System.IO;
using IntelligentCycling.ApiConnector;

class Program {
    static void Main(string[] args) {
        var user = Environment.GetEnvironmentVariable("IC_USER");
        var pass = Environment.GetEnvironmentVariable("IC_PASS");
        var client = new ICClient(user, pass);
        var activities = client.GetNewActivities();

        var outDir = args.Length > 0 ? args[0] : "./activities";
        Directory.CreateDirectory(outDir);

        foreach (var act in activities) {
            var path = Path.Combine(outDir, $"{act.Id}.fit");
            if (!File.Exists(path)) {
                client.DownloadActivity(act.Id, path);
                Console.WriteLine($"Downloaded: {path}");
            }
        }
    }
}
