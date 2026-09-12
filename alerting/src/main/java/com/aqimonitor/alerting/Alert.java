package com.aqimonitor.alerting;

import java.time.LocalDateTime;

public record Alert(String station, LocalDateTime timestamp, AlertType type, String message) {

    public enum AlertType {
        DROPOUT,          // station stopped reporting for too long
        SUSTAINED_UNHEALTHY  // model flagged stuck/outlier for several hours in a row
    }

    @Override
    public String toString() {
        return "[%s] %s @ %s -- %s".formatted(type, station, timestamp, message);
    }
}
