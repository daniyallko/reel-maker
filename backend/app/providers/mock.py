from pathlib import Path

from app.schemas import (
    AssetScore,
    CastCredit,
    CuratedAsset,
    EDLSegment,
    Genre,
    PerceptionResult,
    TrailerEDL,
    VibeProfile,
)

ROLES = {
    Genre.ACTION: ["The Driver", "The Navigator", "The Loose Cannon", "The Informant"],
    Genre.INDIE: ["The Dreamer", "The Realist", "The Wanderer", "The Quiet One"],
    Genre.COMEDY: ["The Mastermind", "The Bad Influence", "The Liability", "The Alibi"],
    Genre.SCIFI: ["The Captain", "The Engineer", "The Signal", "The Survivor"],
}

TITLES = {
    Genre.ACTION: "NO WAY HOME",
    Genre.INDIE: "THE LAST GOLDEN HOUR",
    Genre.COMEDY: "THE BIG SUR INCIDENT",
    Genre.SCIFI: "BEYOND THE WEEKEND",
}


class MockPerceptionProvider:
    async def perceive(
        self,
        assets: list[CuratedAsset],
        cast: list[str],
        notes: str,
        voice_path: Path | None,
    ) -> PerceptionResult:
        eligible = [asset for asset in assets if asset.rejection_reason is None]
        ranked = sorted(
            eligible,
            key=lambda asset: ((index := assets.index(asset)) * 7 % 10, -index),
            reverse=True,
        )[:10]
        kept_ids = {asset.id for asset in ranked}
        hero_id = ranked[0].id if ranked else None
        scores = []
        for index, asset in enumerate(assets):
            kept = asset.id in kept_ids
            scores.append(
                AssetScore(
                    id=asset.id,
                    score=8.8 if asset.id == hero_id else 6.4 + (index % 4) * 0.6,
                    emotion=7 + index % 4,
                    lighting=6 + (index * 3) % 5,
                    action=5 + (index * 2) % 6,
                    kept=kept,
                    hero=asset.id == hero_id,
                    rejection_reason=None if kept else asset.rejection_reason or "Outside the final cut",
                )
            )
        return PerceptionResult(
            assets=scores,
            vibe=VibeProfile(
                transcript=notes or "We definitely did not plan any of this.",
                destination="Big Sur",
                inside_jokes=["Nobody admits who booked the house", "The wrong turn"],
                plot_twists=["The weekend was only supposed to last one night"],
                energy="beautifully unhinged",
            ),
        )


class MockScreenwriterProvider:
    async def write(
        self,
        assets: list[CuratedAsset],
        vibe: VibeProfile,
        cast: list[str],
        genre: Genre,
        notes: str,
    ) -> TrailerEDL:
        kept = [asset for asset in assets if asset.kept]
        if not kept:
            kept = [asset for asset in assets if not asset.rejection_reason]
        if not kept:
            raise ValueError("No usable shots survived the contact sheet.")
        kept = kept[:10]
        duration = 22.0
        segment_duration = duration / len(kept)
        directions = ["zoom_in", "pan_right", "zoom_out", "pan_left"]
        title_cards = {
            0: "THIS SUMMER",
            2: "FOUR FRIENDS",
            4: "ZERO GOOD DECISIONS",
            len(kept) - 1: TITLES[genre],
        }
        voiceovers = {
            0: "Some weekends are planned. This one escaped.",
            2: f"Somewhere near {vibe.destination}, the map stopped mattering.",
            4: "There was a plan. Nobody followed it.",
            len(kept) - 1: "The evidence is finally coming to theaters.",
        }
        segments = []
        for index, asset in enumerate(kept):
            start = round(index * segment_duration, 4)
            end = duration if index == len(kept) - 1 else round((index + 1) * segment_duration, 4)
            segments.append(
                EDLSegment(
                    asset_id=asset.id,
                    act=1 if index < len(kept) / 3 else 2 if index < 2 * len(kept) / 3 else 3,
                    start=start,
                    end=end,
                    ken_burns=directions[index % len(directions)],
                    title_card=title_cards.get(index),
                    voiceover=voiceovers.get(index),
                )
            )
        credits = [
            CastCredit(
                name=name,
                role=ROLES[genre][index % len(ROLES[genre])],
                asset_id=kept[index % len(kept)].id,
            )
            for index, name in enumerate(cast)
        ]
        return TrailerEDL(
            title=TITLES[genre],
            tagline="NO ONE REMEMBERS WHO BOOKED THE HOUSE.",
            duration=duration,
            genre=genre,
            segments=segments,
            cast=credits,
            beat_markers=[0, 3, 6, 11, 14, 17, 20],
        )
