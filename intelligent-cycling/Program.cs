using System;
using System.IO;
using IntelligentCycling.ApiConnector;
using DotNetEnv;

class Program {
    static void Main(string[] args) {
        Env.Load();  // Leser .env-filen
        string user = Environment.GetEnvironmentVariable("IC_USER");
        string pass = Environment.GetEnvironmentVariable("IC_PASS");
        if (string.IsNullOrEmpty(user) || string.IsNullOrEmpty(pass)) {
            Console.Error.WriteLine("ERROR: IC_USER eller IC_PASS ikke satt.");
            return;
        }

        var client = new ICClient(user, pass);
        var activities = client.GetNewActivities();  // Hent nye aktiviteter

        // Angi output-katalog – standard "./activities" eller fra argument
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
