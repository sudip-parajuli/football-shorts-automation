"""Pure narration-to-scene timeline helpers (24 fps)."""
_DATA_TYPES = {"leaderboard", "head_to_head", "timeline", "data_visualization", "data_bars"}
_TEXT_TYPES = {"typewriter_text", "kinetic_stat", "hook_question"}
_MG_TYPES = {"motion_graphic"}

def assign_scene_durations(scenes: list, total_frames: int):
    """
    Distribute total_frames across scenes proportionally by narration_snippet
    word count, then enforce per-type caps/minimums and redistribute excess.
    """
    if not scenes:
        return

    # --- word-count weights ---
    word_counts = []
    for scene in scenes:
        snippet = scene.get("narration_snippet", "")
        words = max(1, len(snippet.split()) if snippet else 5)
        v = scene.get("visual_type", "image")
        if v in _DATA_TYPES:
            words = max(words, 20)      # charts need reading time
        elif v in _TEXT_TYPES:
            words = max(words, 10)
        elif v in _MG_TYPES:
            words = max(words, 8)
        word_counts.append(words)

    if total_frames < len(scenes):
        raise ValueError("Not enough frames for the scene plan")
    total_words = sum(word_counts)

    # --- first pass: proportional ---
    raw = [1 + int((wc / total_words) * (total_frames - len(scenes))) for wc in word_counts]

    # Preserve proportional narration coverage exactly. Long image scenes are
    # split into paced cuts later, rather than donating their time to charts.
    for idx, scene in enumerate(scenes):
        scene["duration_frames"] = raw[idx]
    scenes[-1]["duration_frames"] += total_frames - sum(raw)


def align_scenes_with_voice_timings(scenes: list, timing_data: list, total_frames: int):
    """
    Align scenes to exact spoken word timings using sequential matching.
    """
    if not scenes:
        return
    
    if not timing_data:
        assign_scene_durations(scenes, total_frames)
        return

    # Clean punctuation helper
    def clean_w(w):
        return "".join(c.lower() for c in w if c.isalnum())

    # Prep timed words
    timed_words = []
    for t in timing_data:
        w_clean = clean_w(t.get("word", ""))
        if w_clean:
            timed_words.append({
                "word": w_clean,
                "raw_word": t.get("word", ""),
                "start": t.get("start", 0.0),
                "duration": t.get("duration", 0.0)
            })

    # If timing_data has no clean words, fallback
    if not timed_words:
        assign_scene_durations(scenes, total_frames)
        return

    # Match sequentially
    timed_idx = 0
    num_timed = len(timed_words)

    for s_idx, scene in enumerate(scenes):
        snippet = scene.get("narration_snippet", "")
        if not snippet:
            snippet_words = []
        else:
            snippet_words = [clean_w(w) for w in snippet.split() if clean_w(w)]

        start_time = None
        end_time = None
        matched_timed_words = []

        if not snippet_words:
            # Naive fallback for this specific scene: consume next few words or use current time
            if timed_idx < num_timed:
                start_time = timed_words[timed_idx]["start"]
                # Consume up to 5 words or remaining
                consume_count = min(5, num_timed - timed_idx)
                end_time = timed_words[timed_idx + consume_count - 1]["start"] + timed_words[timed_idx + consume_count - 1]["duration"]
                matched_timed_words = timed_words[timed_idx : timed_idx + consume_count]
                timed_idx += consume_count
            else:
                # No more words left
                start_time = timed_words[-1]["start"] + timed_words[-1]["duration"]
                end_time = start_time
        else:
            # Find candidate start match index
            best_match_idx = timed_idx
            min_diff = len(snippet_words)
            
            # Lookahead window of up to 15 words to handle minor omissions/insertions
            for lookahead in range(min(15, num_timed - timed_idx)):
                candidate_idx = timed_idx + lookahead
                # Calculate how many of the snippet_words match starting here
                matches = 0
                for offset in range(min(len(snippet_words), num_timed - candidate_idx)):
                    if timed_words[candidate_idx + offset]["word"] == snippet_words[offset]:
                        matches += 1
                diff = len(snippet_words) - matches
                if diff < min_diff:
                    min_diff = diff
                    best_match_idx = candidate_idx
                    if min_diff == 0:
                        break # perfect match

            # Consume matching range
            consume_len = len(snippet_words)
            end_match_idx = min(best_match_idx + consume_len, num_timed)
            
            # Extract timings
            matched_slice = timed_words[best_match_idx:end_match_idx]
            if matched_slice:
                start_time = matched_slice[0]["start"]
                end_time = matched_slice[-1]["start"] + matched_slice[-1]["duration"]
                matched_timed_words = matched_slice
                timed_idx = end_match_idx
            else:
                start_time = timed_words[min(timed_idx, num_timed - 1)]["start"]
                end_time = start_time

        # Convert times to frames
        start_frame = int(start_time * 24)
        end_frame = int(end_time * 24)
        scene["_start_frame"] = start_frame
        scene["_matched_words"] = matched_timed_words

    # Boundaries include pauses and rounding without changing total coverage.
    # The first visual starts at frame zero; every following one starts on its
    # spoken passage. Derive durations from adjacent boundaries, not word spans.
    boundaries = [0]
    for index, scene in enumerate(scenes[1:], 1):
        latest = total_frames - (len(scenes) - index)
        boundaries.append(min(latest, max(boundaries[-1] + 1, scene["_start_frame"])))
    boundaries.append(total_frames)
    for index, scene in enumerate(scenes):
        scene["duration_frames"] = boundaries[index + 1] - boundaries[index]

    # Now populate typewriter word timestamps with exact timings relative to the start of the scene
    for scene in scenes:
        if scene.get("visual_type") == "typewriter_text":
            matched = scene.get("_matched_words", [])
            word_timestamps = []
            if matched:
                scene_start_sec = matched[0]["start"]
                for w in matched:
                    rel_start_frame = max(0, int((w["start"] - scene_start_sec) * 24))
                    word_timestamps.append({
                        "word": w["raw_word"],
                        "startFrame": rel_start_frame
                    })
            else:
                # Fallback to linear distribution if no matches
                words = scene.get("typewriter_words", [])
                num_words = len(words)
                for w_idx, w_item in enumerate(words):
                    start_frame = int((w_idx / num_words) * scene["duration_frames"])
                    word_timestamps.append({
                        "word": w_item["word"],
                        "startFrame": start_frame
                    })
            scene["word_timestamps"] = word_timestamps



