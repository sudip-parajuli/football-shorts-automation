export interface VisualScene {
  visual_type:
    | "typewriter_text"
    | "kinetic_stat"
    | "image"
    | "ai_video"
    | "hook_question"
    | "data_bars"
    | "data_visualization"
    | "leaderboard"
    | "head_to_head"
    | "timeline"
    | "motion_graphic"
    | "image_tag";      // alias for "image" — Wikipedia/Wikimedia sourced
  asset_path?: string;          // relative to public/
  asset_type?: "video" | "image_fallback" | "image";
  duration_frames: number;
  transition: "flash" | "fade" | "cut";

  // typewriter_text
  typewriter_words?: Array<{ word: string; weight: string }>;
  word_timestamps?: Array<{ word: string; startFrame: number }>;

  // kinetic_stat
  stat_data?: { value: number; unit: string; label: string };

  // hook_question
  question_text?: string;
  emphasis_phrase?: string;

  // data_bars / data_visualization
  bar_data?: Array<{ label: string; value: number; color?: string }>;
  chart_type?: "bar_chart" | "line_chart";

  // leaderboard
  leaderboard_data?: Array<{ rank: number; name: string; club: string; value: number; unit?: string }>;

  // head_to_head
  head_to_head_data?: {
    playerA: { name: string; value: number; color: string };
    playerB: { name: string; value: number; color: string };
    metric: string;
  };

  // timeline
  timeline_data?: Array<{ year: number; value: number; event?: string }>;
  timeline_title?: string;

  // motion_graphic
  motion_style?: "pulse" | "lines" | "grid" | "particles" | "counter" | "slash";
  accent_color?: string;
  motion_label?: string;
  counter_value?: number;
  counter_unit?: string;

  // image / ai_video / image_tag
  named_entity?: { name: string; description: string };
  ken_burns_style?: string;
  caption?: string;

  // collage: multiple images shown side-by-side (up to 3)
  secondary_asset_path?: string;
}

export interface Chapter {
  chapter_number: number;
  chapter_title: string;
  script: string;
  duration_in_frames: number;
  audio_path: string;
  images: string[];
  visual_scenes?: VisualScene[];
}

export interface MainVideoProps {
  chapters: Chapter[];
  background_music: string;
  image_credits: string[];
  sound_effects?: Record<string, string>; // category -> relative path
  quiz?: {
    question: string;
    options: string[];
    correct_answer_index: number;
    explanation: string;
  };
}
