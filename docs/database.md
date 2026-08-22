# Database

SQLAlchemy 2.0 (typed ORM) + Alembic. Default target is PostgreSQL via
`psycopg`, but the test suite and local demo use a file-based SQLite DB —
the models are dialect-agnostic.

## Entity relationships

```
users 1─∞ websites 1─∞ scans 1─∞ pages 1─∞ resources
                │           │
                │           ├─∞ technologies
                │           ├─∞ findings 1─∞ evidence
                │           ├─∞ recommendations
                │           ├─∞ architecture_nodes 1─∞ architecture_edges
                │           └─1 scan_summary
       1─∞ competitors
```

All child rows cascade on delete (e.g. deleting a website removes its scans,
findings, and recommendations).

## Tables

### users
| Column | Type | Notes |
| --- | --- | --- |
| id | PK | |
| email | varchar(255) | unique, indexed |
| password_hash | varchar(255) | bcrypt |
| full_name | varchar(255) | |
| is_active | boolean | |
| created_at / updated_at | timestamptz | |

### websites
| Column | Type | Notes |
| --- | --- | --- |
| id | PK | |
| user_id | FK users | indexed, cascade |
| name | varchar(255) | |
| url | varchar(2048) | raw input |
| normalized_url | varchar(2048) | indexed; canonical form, duplicate key per user |
| website_type | varchar(32) | portfolio, ecommerce, blog, saas, corporate, education, news, community, other |
| industry / target_audience / description | varchar/text | optional context for analyzers |
| monitoring_enabled | boolean | |
| last_scanned_at | timestamptz | |
| created_at / updated_at | timestamptz | |

### scans
| Column | Type | Notes |
| --- | --- | --- |
| id | PK | |
| website_id | FK websites | cascade |
| status | varchar(32) | QUEUED/CRAWLING/ANALYZING/AI_PROCESSING/COMPLETED/FAILED/CANCELLED, indexed |
| stage | varchar(48) | fine-grained progress stage |
| progress_percent | int | 0–100 |
| error_message | text | on failure |
| crawl_depth / page_limit | int | request params |
| started_at / completed_at | timestamptz | |
| pages_discovered / pages_analyzed | int | |
| overall_score + 8 category scores | float, nullable | `null` = unmeasured category |
| analyzer_status | JSON | per-category status map |

### pages
| Column | Type | Notes |
| --- | --- | --- |
| id | PK | |
| scan_id | FK scans | cascade, indexed |
| url / canonical_url | text | |
| status_code | int | HTTP status observed |
| content_type / title / meta_description | varchar/text | |
| word_count / html_size / load_time | int/int/float | |
| depth | int | crawl depth at discovery |
| is_internal | boolean | |
| created_at | timestamptz | |

### resources
| Column | Type | Notes |
| --- | --- | --- |
| id | PK | |
| scan_id | FK scans | cascade, indexed |
| page_id | FK pages, nullable | |
| url | text | |
| resource_type | varchar(16) | HTML/CSS/JS/IMAGE/FONT/VIDEO/JSON/OTHER |
| mime_type / size_bytes / status_code / load_time | | |
| is_external | boolean | |
| domain | varchar(255) | indexed |

### findings
| Column | Type | Notes |
| --- | --- | --- |
| id | PK | |
| scan_id | FK scans | cascade, indexed |
| category | varchar(32) | SECURITY/PERFORMANCE/ACCESSIBILITY/PRIVACY/SEO/CONTENT/UX/ARCHITECTURE |
| rule_id | varchar(64) | analyzer rule identifier |
| title / description | varchar(500)/text | |
| severity | varchar(16) | CRITICAL/HIGH/MEDIUM/LOW/INFO, indexed |
| confidence | float | 0–1 |
| impact / effort | varchar(16) | CRITICAL/HIGH/MEDIUM/LOW; HIGH/MEDIUM/LOW |
| status | varchar(32) | OPEN/ACKNOWLEDGED/IN_PROGRESS/FIXED/VERIFIED/DISMISSED |
| affected_url | text, nullable | |
| created_at | timestamptz | |

### evidence
| Column | Type | Notes |
| --- | --- | --- |
| id | PK | |
| finding_id | FK findings | cascade |
| evidence_type | varchar(64) | e.g. `header`, `html`, `resource`, `cookie` |
| source / value | text, nullable | e.g. header name / observed value |
| meta | JSON, nullable | structured details |
| confidence | float | |

### recommendations
| Column | Type | Notes |
| --- | --- | --- |
| id | PK | |
| scan_id | FK scans | cascade, indexed |
| title / description | varchar(500)/text | |
| priority | varchar(4) | P0–P3, indexed |
| priority_score | float | computed by `scoring/priority.py` |
| impact / effort / confidence | | |
| category | varchar(32) | |
| root_cause / implementation_guidance | text, nullable | |
| finding_ids | JSON | referenced finding IDs |
| status | varchar(32) | OPEN/IN_PROGRESS/COMPLETED/DISMISSED |
| created_at | timestamptz | |

### technologies
| Column | Type | Notes |
| --- | --- | --- |
| id | PK | |
| scan_id | FK scans | cascade |
| name / category | varchar | e.g. jquery → library |
| confidence | float | |
| evidence | JSON | what triggered detection |

### architecture_nodes / architecture_edges
| Column | Notes |
| --- | --- |
| id, scan_id | |
| node: node_type, name, label, meta (JSON) | e.g. `technology`, `platform`, `resource` |
| edge: source_node_id, target_node_id, relationship | FK to nodes, cascade |

### scan_comparisons (change history)
| Column | Notes |
| --- | --- |
| id, website_id, base_scan_id, compare_scan_id | |
| changes | JSON — structured diff (pages, headers, scores…) |
| summary | AI change explanation |
| created_at | |

### scan_summary
| Column | Notes |
| --- | --- |
| scan_id | PK + FK, one per scan |
| headline / executive_summary | text |
| top_risks / biggest_opportunities / roadmap | JSON arrays |

## Migrations

```bash
cd backend

# Apply all pending migrations
python -m alembic upgrade head

# After changing a model:
python -m alembic revision --autogenerate -m "describe change"
python -m alembic upgrade head
```

Migrations live in `backend/alembic/versions/`. Run
`python -m alembic upgrade head` after pulling new migrations.
