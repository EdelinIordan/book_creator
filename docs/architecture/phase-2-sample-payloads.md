# Phase 2 – Sample Payloads

## Structure Artifact
```json
{
  "project_id": "0c3c1a62-9f00-4d0e-8df2-239104ee0ecc",
  "version": 2,
  "created_at": "2025-09-29T15:20:00Z",
  "updated_at": "2025-09-29T15:45:03Z",
  "synopsis": "A comparative history of empires emphasising administrative innovation.",
  "chapters": [
    {
      "id": "0d3e6404-0321-46c1-8f79-740a3a4f3d0d",
      "title": "Origins of Empire",
      "summary": "Examines catalysts that led to empire formation.",
      "order": 1,
      "narrative_arc": "Establish stakes and introduce core persona.",
      "subchapters": [
        {
          "id": "a9f6fc87-98d4-481b-ae87-2c21d4b4a150",
          "title": "Resource Accumulation",
          "summary": "How surplus made sustained campaigns possible.",
          "order": 1,
          "learning_objectives": [
            "Understand economic preconditions.",
            "Introduce primary research sources."
          ],
          "related_subchapters": []
        }
      ]
    }
  ]
}
```

## Research Fact
```json
{
  "id": "5c8c2158-5a92-4c6d-8336-600b6f9a9ce6",
  "project_id": "0c3c1a62-9f00-4d0e-8df2-239104ee0ecc",
  "subchapter_id": "a9f6fc87-98d4-481b-ae87-2c21d4b4a150",
  "summary": "Grain levy records reveal a 15% surplus redirected to campaign logistics.",
  "detail": "Papyrus archives from 320 BCE enumerate grain levies...",
  "citation": {
    "source_title": "Harvests of Power",
    "author": "Leila Karim",
    "publication_date": "2021",
    "url": "https://doi.org/10.1234/harvests",
    "page": "pp. 45-48",
    "source_type": "academic_journal"
  },
  "created_at": "2025-09-29T16:05:14Z"
}
```

## Agent Message with Critiques
```json
{
  "id": "6500720a-5c28-4d8b-a0a8-279b0354730a",
  "project_id": "0c3c1a62-9f00-4d0e-8df2-239104ee0ecc",
  "stage": "FACT_MAPPING",
  "role": "fact_critic",
  "content": "The proposed fact lacks a primary citation and duplicates an earlier logistics insight.",
  "created_at": "2025-09-29T16:22:01Z",
  "critiques": [
    {
      "id": "2fd8407a-d17b-4421-9a51-347fa394bab7",
      "severity": "warning",
      "summary": "Duplicate logistics insight",
      "details": "Fact overlaps with subchapter Logistics Foundations (fact e180...).",
      "target_reference": "a9f6fc87-98d4-481b-ae87-2c21d4b4a150",
      "applied": false
    }
  ],
  "resulting_artifact_ids": []
}
```

These examples demonstrate how Python Pydantic models and TypeScript Zod schemas serialize shared data for the orchestrator, workers, and frontend.
