package com.aqimonitor.alerting;

import org.junit.jupiter.api.Test;

import java.time.LocalDateTime;
import java.util.List;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

class AlertEngineTest {

    private static LocalDateTime hour(int h) {
        return LocalDateTime.of(2024, 1, 1, 0, 0).plusHours(h);
    }

    @Test
    void firesDropoutAlertAfterFourHourGap() {
        AlertEngine engine = new AlertEngine();
        engine.process(new StationReading("ito-cpcb", hour(0), false));

        // 3-hour gap: below threshold, no alert yet
        List<Alert> noAlertYet = engine.process(new StationReading("ito-cpcb", hour(3), false));
        assertTrue(noAlertYet.isEmpty());

        // Jump to a 4+ hour gap from the last reading (hour 3 -> hour 8 = 5hr gap)
        List<Alert> alerts = engine.process(new StationReading("ito-cpcb", hour(8), false));
        assertEquals(1, alerts.size());
        assertEquals(Alert.AlertType.DROPOUT, alerts.get(0).type());
    }

    @Test
    void doesNotFireDropoutForShortGaps() {
        AlertEngine engine = new AlertEngine();
        engine.process(new StationReading("ito-cpcb", hour(0), false));
        List<Alert> alerts = engine.process(new StationReading("ito-cpcb", hour(2), false));
        assertTrue(alerts.isEmpty());
    }

    @Test
    void firesSustainedUnhealthyOnlyAtThreeConsecutive() {
        AlertEngine engine = new AlertEngine();
        engine.process(new StationReading("ito-cpcb", hour(0), true));
        List<Alert> secondUnhealthy = engine.process(new StationReading("ito-cpcb", hour(1), true));
        assertTrue(secondUnhealthy.isEmpty(), "should not fire on 2nd consecutive unhealthy reading");

        List<Alert> thirdUnhealthy = engine.process(new StationReading("ito-cpcb", hour(2), true));
        assertEquals(1, thirdUnhealthy.size());
        assertEquals(Alert.AlertType.SUSTAINED_UNHEALTHY, thirdUnhealthy.get(0).type());
    }

    @Test
    void doesNotFireSustainedAlertForSingleNoisyReading() {
        AlertEngine engine = new AlertEngine();
        engine.process(new StationReading("ito-cpcb", hour(0), true));
        engine.process(new StationReading("ito-cpcb", hour(1), false)); // breaks the streak
        List<Alert> alerts = engine.process(new StationReading("ito-cpcb", hour(2), true));
        assertTrue(alerts.isEmpty(), "a single healthy reading should reset the streak");
    }

    @Test
    void tracksMultipleStationsIndependently() {
        AlertEngine engine = new AlertEngine();
        engine.process(new StationReading("station-a", hour(0), true));
        engine.process(new StationReading("station-b", hour(0), false));
        engine.process(new StationReading("station-a", hour(1), true));
        List<Alert> alerts = engine.process(new StationReading("station-a", hour(2), true));

        assertEquals(1, alerts.size());
        assertEquals("station-a", alerts.get(0).station());
    }
}
