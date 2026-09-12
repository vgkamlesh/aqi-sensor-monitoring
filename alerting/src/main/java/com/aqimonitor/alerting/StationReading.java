package com.aqimonitor.alerting;

import java.time.LocalDateTime;

/**
 * One reading: a station reported (or should have reported) at a given hour,
 * and whether the model/rule flagged it unhealthy (stuck or outlier).
 * Dropout is NOT a field here -- it's detected by the AlertEngine from GAPS
 * between consecutive readings of the same station, since a missing hour
 * produces no row at all in the input CSV.
 */
public record StationReading(String station, LocalDateTime timestamp, boolean unhealthy) {
}
