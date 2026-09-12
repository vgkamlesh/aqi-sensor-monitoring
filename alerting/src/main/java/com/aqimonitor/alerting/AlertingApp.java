package com.aqimonitor.alerting;

import java.nio.file.Path;
import java.util.Comparator;
import java.util.List;

/**
 * Entry point. Reads a predictions CSV (timestamp,station,unhealthy),
 * replays it through the AlertEngine in chronological order, and prints
 * every alert fired. In a real deployment this would tail a live feed
 * instead of reading a static file -- the engine itself doesn't care
 * where readings come from.
 */
public class AlertingApp {

    public static void main(String[] args) throws Exception {
        String csvPath = args.length > 0 ? args[0] : "processed_data/predictions.csv";
        List<StationReading> readings = CsvPredictionReader.read(Path.of(csvPath));
        readings.sort(Comparator.comparing(StationReading::timestamp));

        System.out.printf("Loaded %d readings from %s%n", readings.size(), csvPath);

        AlertEngine engine = new AlertEngine();
        int alertCount = 0;
        for (StationReading reading : readings) {
            for (Alert alert : engine.process(reading)) {
                System.out.println(alert);
                alertCount++;
            }
        }

        System.out.printf("%nDone. %d alerts fired across %d readings.%n", alertCount, readings.size());
    }
}
