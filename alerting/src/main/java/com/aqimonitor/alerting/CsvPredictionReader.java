
package com.aqimonitor.alerting;

import java.io.BufferedReader;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.List;

public class CsvPredictionReader {

    private static final DateTimeFormatter TS_FORMAT_4 =
            DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss");

    private static final DateTimeFormatter TS_FORMAT_2 =
            DateTimeFormatter.ofPattern("yy-MM-dd HH:mm:ss");

    public static List<StationReading> read(Path csvPath) throws IOException {
        List<StationReading> readings = new ArrayList<>();

        try (BufferedReader reader = Files.newBufferedReader(csvPath)) {
            String header = reader.readLine();
            String line;

            while ((line = reader.readLine()) != null) {
                if (line.isBlank()) continue;

                String[] parts = line.split(",", -1);

                if (parts.length < 3) continue;

                LocalDateTime timestamp;

                try {
                    timestamp = LocalDateTime.parse(
                            parts[0].trim(), TS_FORMAT_4
                    );
                } catch (DateTimeParseException e) {
                    timestamp = LocalDateTime.parse(
                            parts[0].trim(), TS_FORMAT_2
                    );
                }

                String station = parts[1].trim();
                boolean unhealthy = parts[2].trim().equals("1");

                readings.add(new StationReading(
                        station, timestamp, unhealthy
                ));
            }
        }

        return readings;
    }
}
