#include <Arduino.h>
#include <HX711.h>

// Pin-Konfiguration für Zelle links
#define DOUT_PIN_1 A4  // DOUT-Pin des HX711 (links)
#define SCK_PIN_1  A6  // PD_SCK-Pin des HX711 (links)

// Pin-Konfiguration für Zelle rechts
#define DOUT_PIN_2 D7  // DOUT-Pin des HX711 (rechts)
#define SCK_PIN_2  D5  // PD_SCK-Pin des HX711 (rechts)

// HX711-Instanzen erstellen
HX711 scale_left;
HX711 scale_right;

void setup() {
    // Seriellen Monitor starten
    Serial.begin(115200);
    delay(500);

    // HX711 initialisieren - linke Zelle
    scale_left.begin(DOUT_PIN_1, SCK_PIN_1);
    scale_left.set_gain(128);
    // Kalibrierwert anpassen
    scale_left.set_scale(15244.f);
    scale_left.tare();  // Nullpunkt setzen

    // HX711 initialisieren - rechte Zelle
    scale_right.begin(DOUT_PIN_2, SCK_PIN_2);
    scale_right.set_gain(128);
    // Kalibrierwert anpassen
    scale_right.set_scale(15244.f);
    scale_right.tare(); // Nullpunkt setzen

    Serial.println("HX711 ist bereit!");
}

void loop() {
    // Linke Zelle auslesen
    if (scale_left.is_ready()) {
        float gewicht_links = scale_left.get_units(10); // Durchschnitt aus 10 Messungen
        Serial.print("Gewicht links: ");
        Serial.print(gewicht_links);
        Serial.println(" kg");
    } else {
        Serial.println("HX711 (links) nicht bereit!");
    }

    // Rechte Zelle auslesen
    if (scale_right.is_ready()) {
        float gewicht_rechts = scale_right.get_units(10); // Durchschnitt aus 10 Messungen
        Serial.print("Gewicht rechts: ");
        Serial.print(gewicht_rechts);
        Serial.println(" kg");
    } else {
        Serial.println("HX711 (rechts) nicht bereit!");
    }

    delay(500);
}
