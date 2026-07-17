"""PromptBuilder — assembles AI coaching prompts from lap summaries.

Reference lap hierarchy (per project principle):
    1. Session-best lap, if the session has 2+ valid laps
    2. All-time best lap for the track, if prior sessions exist
    3. General observations only (no comparison), if neither is available
       — typically the driver's very first lap on a track.

The prompt explicitly asks the AI to stay sector-based and avoid
unverifiable micro-claims (e.g. exact braking distances), matching the
project's feedback-scope principle.
"""

from dataclasses import dataclass
from enum import Enum

from f1_coach.domain.models.f125.car_setup import CarSetup
from f1_coach.domain.models.f125.enums import TrackName
from f1_coach.application.f125.telemetry_analyzer import LapSummary, SectorSummary
from f1_coach.domain.models.f125.lap import Lap
from f1_coach.domain.models.f125.session import Session


class ReferenceLevel(Enum):
    SESSION_BEST = "session_best"
    TRACK_BEST = "track_best"
    NONE = "none"


@dataclass(frozen=True, slots=True)
class ReferenceContext:
    """Which reference lap (if any) is being used, and why."""

    level: ReferenceLevel
    reference_summary: LapSummary | None


_SYSTEM_PREAMBLE = (
    "Sen profesyonel bir F1 yarış mühendisisin. Sürücüye doğrudan, kendisine "
    "hitap ederek konuşuyorsun — telsizden konuşan bir yarış mühendisi gibi. "
    "Tur telemetrisine dayanarak her sektör için kısa ve uygulanabilir koçluk "
    "geri bildirimi hazırlıyorsun.\n\n"
    "KURALLAR:\n"
    "1. Yalnızca sektör bazlı gözlemler yap; frenleme noktası, apex mesafesi gibi "
    "metre cinsinden ölçülemeyen iddialardan kaçın.\n"
    "2. Geri bildirimini ortalama hız, gaz/fren kullanım oranı, tam gaz yüzdesi gibi "
    "toplu istatistiklere dayandır.\n"
    "3. Sürücüye DOĞRUDAN hitap et — 'sürücü', 'pilot' gibi üçüncü şahıs ifadeler "
    "yerine 'sen', 'senin', 'yaptın', 'kazandın' gibi ikinci tekil şahıs kullan. "
    "Türkçe, net ve gerçekçi bir üslup kullan; zayıf yönleri pozitif bir dille "
    "açıklayarak geliştirici öneriler sun.\n"
    "4. Her sektör için en fazla 3-4 cümle yaz; cümleler öz, doğrudan ve eyleme "
    "geçirilebilir olmalı.\n"
    "5. Tur ve sektör sürelerinden bahsederken SADECE sana verilen formatı "
    "(dakika:saniye.milisaniye, örn. 1:08.690) kullan; asla saniyeye çevirip "
    "yeniden ifade etme.\n\n"
    "İSTENEN ÇIKTI YAPISI:\n"
    "- Giriş: senin mevcut performansını özetleyen 2-3 cümle.\n"
    "- Sektör 1, 2 ve 3 için ayrı ayrı, kurallara uygun kısa koçluk notları.\n"
    "- Kapanış: genel iyileştirme önerileri ve bir sonraki turda odaklanman "
    "gereken temel nokta(lar), 2-3 cümle.\n"
)

def _format_time(seconds: float) -> str:
    """Saniyeyi dakika:saniye.milisaniye formatına çevirir (örn. 68.690 → 1:08.690)."""
    minutes, secs = divmod(seconds, 60)
    return f"{int(minutes)}:{secs:06.3f}"

def _format_sector(sector: SectorSummary) -> str:
    return (
        f"  Sektör {sector.sector_number}: {_format_time(sector.sector_time)} | "
        f"ort. hız {sector.avg_speed:.0f} km/s, maks {sector.max_speed:.0f} km/s | "
        f"tam gaz %{sector.full_throttle_pct:.0f} | "
        f"fren kullanımı %{sector.braking_frames_pct:.0f} | "
        f"DRS %{sector.drs_usage_pct:.0f}"
    )

def _format_lap_block(label: str, summary: LapSummary) -> str:
    lines = [f"{label} (Tur {summary.lap_number}, {_format_time(summary.lap_time)}):"]
    lines.extend(_format_sector(s) for s in summary.sectors)
    return "\n".join(lines)


def determine_reference(
    session_best: LapSummary | None,
    track_best: LapSummary | None,
    session_valid_lap_count: int,
) -> ReferenceContext:
    """Apply the reference lap hierarchy to pick which comparison to use.

    Args:
        session_best:           Best lap summary in the current session, if any.
        track_best:              All-time best lap summary for this track, if any.
        session_valid_lap_count: Number of valid laps completed in the current
                                 session so far (excludes the lap being analyzed).

    Returns:
        ReferenceContext indicating which reference (if any) to use.
    """
    if session_valid_lap_count >= 2 and session_best is not None:
        return ReferenceContext(ReferenceLevel.SESSION_BEST, session_best)
    if track_best is not None:
        return ReferenceContext(ReferenceLevel.TRACK_BEST, track_best)
    return ReferenceContext(ReferenceLevel.NONE, None)


def build_conditions_note(
    current_lap: Lap,
    reference_lap: Lap | None,
    current_session: Session,
    reference_session: Session | None,
) -> str | None:
    """Build a short context note about track conditions and assist mismatch.

    Returns None if there is nothing noteworthy to mention (no reference lap,
    or reference/current share the same conditions and assist configuration).

    Two things this note covers:
      - Track/air temperature context for the current lap — always included
        when there is a reference lap, since it explains grip differences.
      - Assist mismatch warning — assists are a player setting, and comparing
        a lap driven with e.g. the racing line assist on against one without
        it produces a misleading sense of "improvement" or "regression".
        This is a soft warning, not a hard filter (unlike weather/safety car,
        which are excluded from reference selection entirely).
    """
    if reference_lap is None or reference_session is None:
        return None

    lines = [
        f"Mevcut tur koşulları: {current_lap.weather.display_name}, "
        f"pist sıcaklığı {current_lap.track_temperature}°C, "
        f"hava sıcaklığı {current_lap.air_temperature}°C."
    ]

    mismatched = []
    if current_session.steering_assist != reference_session.steering_assist:
        mismatched.append("direksiyon asisti")
    if current_session.braking_assist != reference_session.braking_assist:
        mismatched.append("fren asisti")
    if current_session.gearbox_assist != reference_session.gearbox_assist:
        mismatched.append("vites asisti")
    if current_session.dynamic_racing_line != reference_session.dynamic_racing_line:
        mismatched.append("sürüş çizgisi rehberi")

    if mismatched:
        lines.append(
            "Not: referans tur ile mevcut tur arasında şu asist ayarlarında "
            f"fark var: {', '.join(mismatched)}. Bu farkı göz önünde bulundurarak "
            "değerlendirme yap, performans farkını doğrudan sürüş becerisine bağlama."
        )

    return " ".join(lines)


def build_post_lap_prompt(
    current: LapSummary,
    reference: ReferenceContext,
    conditions_note: str | None = None,
) -> str:
    """Build the full prompt for post-lap AI feedback generation.

    Args:
        current:         Summary of the lap just completed.
        reference:        Result of determine_reference() — may carry no reference lap.
        conditions_note:  Optional context string from build_conditions_note(),
                          covering track conditions and any assist mismatch.

    Returns:
        A complete prompt string ready to send to an AIAdapter.
    """
    parts = [_SYSTEM_PREAMBLE, "", _format_lap_block("MEVCUT TUR", current)]

    if reference.level == ReferenceLevel.SESSION_BEST and reference.reference_summary:
        parts.append("")
        parts.append(_format_lap_block("REFERANS (Bu session'daki en iyi tur)", reference.reference_summary))
        parts.append("")
        parts.append(
            "Mevcut turu referans turla sektör sektör karşılaştır. Hangi sektörde "
            "zaman kaybedildiğini ve olası nedenini (gaz/fren kullanımına dayanarak) belirt."
        )
    elif reference.level == ReferenceLevel.TRACK_BEST and reference.reference_summary:
        parts.append("")
        parts.append(_format_lap_block("REFERANS (Bu pistteki tüm zamanların en iyisi)", reference.reference_summary))
        parts.append("")
        parts.append(
            "Bu, sürücünün bu session'daki ilk geçerli turu olduğu için pistteki "
            "en iyi geçmiş turla karşılaştır. Genel eğilimleri vurgula."
        )
    else:
        parts.append("")
        parts.append(
            "Bu, sürücünün bu pistteki ilk turu. Karşılaştırma yapma — yalnızca "
            "sektör verilerine dayanarak genel gözlemler ve öneriler sun."
        )

    if conditions_note:
        parts.append("")
        parts.append(conditions_note)

    return "\n".join(parts)


def build_comparison_prompt(lap_a: LapSummary, lap_b: LapSummary) -> str:
    """Build a prompt for explicit two-lap comparison (UI 'Karşılaştırmalı Analiz').

    Unlike build_post_lap_prompt, both laps are provided directly by the user's
    selection in the UI — no reference-lap hierarchy is applied here.
    """
    parts = [
        _SYSTEM_PREAMBLE,
        "",
        _format_lap_block("TUR A", lap_a),
        "",
        _format_lap_block("TUR B", lap_b),
        "",
        "İki turu sektör sektör karşılaştır. Hangi turun hangi sektörde daha "
        "iyi performans gösterdiğini ve olası nedenini belirt.",
    ]
    return "\n".join(parts)

# ---------------------------------------------------------------------------
# Setup analizi promptları
# ---------------------------------------------------------------------------

_SETUP_SYSTEM_PREAMBLE = (
    "Sen profesyonel bir F1 yarış mühendisisin. Sürücüye doğrudan hitap ederek "
    "araç setup'ı hakkında yorum yapıyorsun.\n\n"
    "KURALLAR:\n"
    "1. Setup değerlerine dayanarak GENEL mühendislik trade-off'larını açıkla "
    "(ör. 'yüksek ön kanat dönüşlerde tutuşu artırır ama düz hızda kayıp yaratabilir').\n"
    "2. ASLA kesin zaman kazanç/kayıp iddiası yapma (ör. '0.3 saniye kazandırır') — "
    "bu setup verisiyle doğrulanamaz bir iddiadır, çünkü elindeki veri iki setup'ın "
    "aynı koşulda karşılaştırmalı sürülmüş telemetrisi değil.\n"
    "3. Sürücüye DOĞRUDAN hitap et — 'sen', 'senin' gibi ikinci tekil şahıs kullan.\n"
    "4. Setup'ın hangi sürüş tarzına (agresif/dengeli/stabil) uygun olduğunu "
    "değerlendirebilirsin ama bunu da genel mühendislik bilgisine dayandır.\n"
    "5. Türkçe, net ve öz yaz; toplam 4-6 cümleyi geçme.\n"
)

# UI'daki gösterim etiketlerinden bağımsız tutuluyor (application katmanı
# presentation katmanına bağımlı olmamalı) — fuel_load kasıtlı olarak
# hariç, turdan tura doğal olarak azaldığı için mühendislik yorumuna konu değil.
_SETUP_PROMPT_FIELD_LABELS: list[tuple[str, str]] = [
    ("front_wing", "Ön kanat"),
    ("rear_wing", "Arka kanat"),
    ("on_throttle_diff", "Diferansiyel (gaz açıkken) %"),
    ("off_throttle_diff", "Diferansiyel (gaz kapalıyken) %"),
    ("front_camber", "Ön kamber"),
    ("rear_camber", "Arka kamber"),
    ("front_toe", "Ön toe"),
    ("rear_toe", "Arka toe"),
    ("front_suspension", "Ön süspansiyon sertliği"),
    ("rear_suspension", "Arka süspansiyon sertliği"),
    ("front_arb", "Ön anti-roll bar"),
    ("rear_arb", "Arka anti-roll bar"),
    ("front_ride_height", "Ön yerden yükseklik"),
    ("rear_ride_height", "Arka yerden yükseklik"),
    ("brake_pressure", "Fren basıncı %"),
    ("brake_bias", "Fren dengesi (ön) %"),
    ("front_left_tyre_pressure", "Ön sol lastik basıncı (PSI)"),
    ("front_right_tyre_pressure", "Ön sağ lastik basıncı (PSI)"),
    ("rear_left_tyre_pressure", "Arka sol lastik basıncı (PSI)"),
    ("rear_right_tyre_pressure", "Arka sağ lastik basıncı (PSI)"),
    ("ballast", "Balast"),
]


def _format_setup_block(label: str, setup: CarSetup) -> str:
    lines = [f"{label} (Tur {setup.valid_from_lap}'den itibaren geçerli):"]
    for field_name, field_label in _SETUP_PROMPT_FIELD_LABELS:
        lines.append(f"  {field_label}: {getattr(setup, field_name)}")
    return "\n".join(lines)


def build_setup_single_prompt(setup: CarSetup, track: TrackName) -> str:
    """Build the prompt for single-setup AI analysis (persisted feedback)."""
    parts = [
        _SETUP_SYSTEM_PREAMBLE, "",
        f"Pist: {track.display_name}", "",
        _format_setup_block("SETUP", setup), "",
        "Bu setup'ı genel olarak değerlendir: hangi sürüş tarzına uygun, "
        "hangi trade-off'ları içeriyor?",
    ]
    return "\n".join(parts)


def build_setup_comparison_prompt(
    setup_a: CarSetup, setup_b: CarSetup, track: TrackName
) -> str:
    """Build the prompt for two-setup AI comparison (not persisted)."""
    parts = [
        _SETUP_SYSTEM_PREAMBLE, "",
        f"Pist: {track.display_name}", "",
        _format_setup_block("SETUP A", setup_a), "",
        _format_setup_block("SETUP B", setup_b), "",
        "İki setup'ı karşılaştır: hangi farklar var, bu farklar hangi genel "
        "mühendislik trade-off'larına işaret ediyor?",
    ]
    return "\n".join(parts)