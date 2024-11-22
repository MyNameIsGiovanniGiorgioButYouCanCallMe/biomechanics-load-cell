#include <Arduino.h>
#include <HX711.h>

// Pin-Konfiguration
#define DOUT_PIN A4  // DOUT-Pin des HX711
#define SCK_PIN A6   // PD_SCK-Pin des HX711

// HX711-Instanz erstellen
HX711 scale;

void setup() {
    // Seriellen Monitor starten
    Serial.begin(115200);
    delay(500);

    // HX711 initialisieren
    scale.begin(DOUT_PIN, SCK_PIN);

    // Optional: Verstärkung einstellen (Standard: 128)
    scale.set_gain(128);

    // Kalibrierungswert setzen (Wert anpassen, um das richtige Gewicht zu erhalten)
    scale.set_scale(2280.f); // todo: Beispiel-Kalibrierwert evtl noch Kalibrieren
    scale.tare();            // Tare: Gewicht auf Null setzen

    Serial.println("HX711 ist bereit!");
}

void loop() {
    // Gewicht in Einheiten auslesen
    if (scale.is_ready()) {
        float gewicht = scale.get_units(10); // Durchschnitt von 10 Messungen
        Serial.print("Gewicht: ");
        Serial.print(gewicht);
        Serial.println(" kg");
    } else {
        Serial.println("HX711 nicht bereit!");
    }

    delay(500);
}