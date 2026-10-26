from app.services.hazard import classify_flood_alert

def main():
    test_cases = [
        ("River overflow warning: Musi river levels exceeding danger mark", "RIVER_OVERFLOW"),
        ("Urban waterlogging and street inundation in Secunderabad", "URBAN_INUNDATION"),
        ("Flood-related heavy rainfall warning: intense localized flooding likely", "FLOOD_RELATED_HEAVY_RAINFALL"),
        ("Flash flood emergency near catchment area", "FLASH_FLOOD"),
        ("General flood alert for low-lying residential sectors", "FLOOD"),
        ("Tsunami warning issued for eastern coastline after deep sea seismic activity", None),
        ("Earthquake of magnitude 6.2 recorded with epicentre 50km deep", None),
        ("Very severe cyclonic storm approaching coastline with gusty winds", None),
        ("Active forest wildfire spreading across western ridge", None),
        ("Major landslide blocking mountain pass and highway", None),
        ("Snow avalanche advisory for higher peaks", None),
        ("Severe drought conditions and heatwave alert", None),
        ("Passing light showers expected in evening", None),
        ("Isolated lightning and thunder activity", None),
    ]

    print("Verifying representative alerts against classify_flood_alert:")
    for text, expected in test_cases:
        res = classify_flood_alert(text)
        actual_type = res[0] if res else None
        assert actual_type == expected, f"Failed for '{text}': expected {expected}, got {actual_type}"
        status_label = f"CLASSIFIED AS {actual_type}" if actual_type else "EXCLUDED (NON-FLOOD / AMBIGUOUS)"
        print(f"  [OK] '{text[:48]}...' -> {status_label}")

    print("\nAll 14 representative alert tests passed successfully!")

if __name__ == "__main__":
    main()
