export type BookStructure = {
  project_id: string;
  version: number;
  created_at: string;
  updated_at: string;
  synopsis?: string | null;
  chapters: Array<{
    id: string;
    title: string;
    summary: string;
    order: number;
    narrative_arc?: string | null;
    subchapters: Array<{
      id: string;
      title: string;
      summary: string;
      order: number;
      learning_objectives: string[];
      related_subchapters: string[];
    }>;
  }>;
};
