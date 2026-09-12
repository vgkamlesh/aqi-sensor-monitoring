package com.aqimonitor.alerting;

import java.time.Duration;
import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;

/**
 * Fires alerts from a stream of StationReadings, per the rules in
 * docs/health_definition.md:
 *   - DROPOUT: a station goes DROPOUT_THRESHOLD_HOURS or more without a
 *     reading. Detected purely from the gap between consecutive timestamps
 *     for that station -- no model needed, this is a direct rule check.
 *   - SUSTAINED_UNHEALTHY: the model/rule flagged a station unhealthy for
 *     SUSTAINED_THRESHOLD consecutive readings. Requiring several in a row
 *     (not just one noisy timestamp) avoids alert flapping.
 *
 * Readings must be fed in chronological order PER STATION (across stations,
 * any interleaving is fine -- each station's state is tracked separately).
 */
public class AlertEngine {

    public static final int DROPOUT_THRESHOLD_HOURS = 4;
    public static final int SUSTAINED_THRESHOLD = 3;

    private final Map<String, LocalDateTime> lastSeen = new HashMap<>();
    private final Map<String, Integer> unhealthyStreak = new HashMap<>();
    private final Map<String, Boolean> dropoutAlertActive = new HashMap<>();
    private final Map<String, Boolean> sustainedAlertActive = new HashMap<>();

    public List<Alert> process(StationReading reading) {
        List<Alert> alerts = new ArrayList<>();
        String station = reading.station();

        // --- Dropout check: gap since this station's last reading ---
        LocalDateTime previous = lastSeen.get(station);
        if (previous != null) {
            long gapHours = Duration.between(previous, reading.timestamp()).toHours();
            boolean isDropout = gapHours >= DROPOUT_THRESHOLD_HOURS;
            boolean alreadyAlerted = dropoutAlertActive.getOrDefault(station, false);

            if (isDropout && !alreadyAlerted) {
                alerts.add(new Alert(station, reading.timestamp(), Alert.AlertType.DROPOUT,
                        "No reading for %d hours (last seen %s)".formatted(gapHours, previous)));
                dropoutAlertActive.put(station, true);
            } else if (!isDropout) {
                dropoutAlertActive.put(station, false); // station recovered, reset
            }
        }
        lastSeen.put(station, reading.timestamp());

        // --- Sustained unhealthy check ---
        int streak = reading.unhealthy() ? unhealthyStreak.getOrDefault(station, 0) + 1 : 0;
        unhealthyStreak.put(station, streak);

        boolean crossedThreshold = streak == SUSTAINED_THRESHOLD; // fire once, at the crossing point
        if (crossedThreshold) {
            alerts.add(new Alert(station, reading.timestamp(), Alert.AlertType.SUSTAINED_UNHEALTHY,
                    "%d consecutive unhealthy readings".formatted(streak)));
            sustainedAlertActive.put(station, true);
        } else if (streak == 0) {
            sustainedAlertActive.put(station, false); // station recovered, reset
        }

        return alerts;
    }
}
