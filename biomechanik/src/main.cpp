#include <Arduino.h>
#include <HX711.h>

// ---------------------------------------------
// Konfiguration Linke Wägezelle (5V Versorgung)
// ---------------------------------------------
#define DOUT_PIN_1 A4 // DOUT-Pin des HX711 (links)
#define SCK_PIN_1 A6  // PD_SCK-Pin des HX711 (links)
// HX711 links: VCC auf 5V, RATE-Pin auf GND (nicht auf HIGH legen).

// ---------------------------------------------
// Konfiguration Rechte Wägezelle (3,3V Versorgung)
// ---------------------------------------------
#define DOUT_PIN_2 7 // DOUT-Pin des HX711 (rechts) - vormals D7
#define SCK_PIN_2 5  // PD_SCK-Pin des HX711 (rechts) - vormals D5
// HX711 rechts: VCC auf 3,3V, RATE-Pin auf GND (nicht auf HIGH legen).

HX711 scale_left;
HX711 scale_right;

void setup()
{
    Serial.begin(115200);
    delay(500);

    // Linke Zelle initialisieren (5V Versorgung, 10 Hz)
    scale_left.begin(DOUT_PIN_1, SCK_PIN_1);
    scale_left.set_gain(128);
    scale_left.set_scale(15362.f);
    scale_left.tare(); // Nullpunkt setzen

    // Rechte Zelle initialisieren (3,3V Versorgung, 10 Hz)
    scale_right.begin(DOUT_PIN_2, SCK_PIN_2);
    scale_right.set_gain(128);
    scale_right.set_scale(15265.f);
    scale_right.tare(); // Nullpunkt setzen

    Serial.println("HX711 ist im 10 Hz-Modus bereit!");
}

void loop()
{
    // Linke Zelle auslesen
    if (scale_left.is_ready())
    {
        float gewicht_links = scale_left.get_units(1); // Mittelwert aus 10 Messungen
        Serial.print("Gewicht links [kg]: ");
        Serial.println(gewicht_links, 5);
    }
    else
    {
        Serial.println("HX711 (links) nicht bereit!");
    }

    // Rechte Zelle auslesen
    if (scale_right.is_ready())
    {
        float gewicht_rechts = scale_right.get_units(1);
        Serial.print("Gewicht rechts [kg]: ");
        Serial.println(gewicht_rechts, 5);
    }
    else
    {
        Serial.println("HX711 (rechts) nicht bereit!");
    }

    // 10 Hz ≈ alle 100ms eine Messung
    delay(100);
}
