"""
mas.memory.comms_vault: Communication Vault & Cognitive Linguistic Profiler.
Records every user communication into a local SQLite database to track understanding,
measure engagement, and train AI agents on user vocabulary and conversational style.

Architect: Acinonyx
"""

from __future__ import annotations

import contextlib
import json
import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional


DEFAULT_DB_PATH = Path(
    os.environ.get("MAS_COMMS_VAULT_DB", Path(__file__).resolve().parents[2] / "workspace" / "data" / "comms_vault.db")
)
DEFAULT_BRAIN_DIR = Path(os.environ.get("MAS_BRAIN_DIR", "/home/acinonyx/.gemini/antigravity/brain"))

STOPWORDS = {
    'a', 'about', 'above', 'after', 'again', 'against', 'all', 'am', 'an', 'and', 'any', 'are', 'aren\'t',
    'as', 'at', 'be', 'because', 'been', 'before', 'being', 'below', 'between', 'both', 'but', 'by', 'can',
    'can\'t', 'cannot', 'could', 'couldn\'t', 'did', 'didn\'t', 'do', 'does', 'doesn\'t', 'doing', 'don\'t',
    'down', 'during', 'each', 'few', 'for', 'from', 'further', 'had', 'hadn\'t', 'has', 'hasn\'t', 'have',
    'haven\'t', 'having', 'he', 'he\'d', 'he\'ll', 'he\'s', 'her', 'here', 'here\'s', 'hers', 'herself',
    'him', 'himself', 'his', 'how', 'how\'s', 'i', 'i\'d', 'i\'ll', 'i\'m', 'i\'ve', 'if', 'in', 'into',
    'is', 'isn\'t', 'it', 'it\'s', 'its', 'itself', 'let\'s', 'me', 'more', 'most', 'mustn\'t', 'my',
    'myself', 'no', 'nor', 'not', 'of', 'off', 'on', 'once', 'only', 'or', 'other', 'ought', 'our', 'ours',
    'ourselves', 'out', 'over', 'own', 'same', 'shan\'t', 'she', 'she\'d', 'she\'ll', 'she\'s', 'should',
    'shouldn\'t', 'so', 'some', 'such', 'than', 'that', 'that\'s', 'the', 'their', 'theirs', 'them',
    'themselves', 'then', 'there', 'there\'s', 'these', 'they', 'they\'d', 'they\'ll', 'they\'re', 'they\'ve',
    'this', 'those', 'through', 'to', 'too', 'under', 'until', 'up', 'very', 'was', 'wasn\'t', 'we', 'we\'d',
    'we\'ll', 'we\'re', 'we\'ve', 'were', 'weren\'t', 'what', 'what\'s', 'when', 'when\'s', 'where', 'where\'s',
    'which', 'while', 'who', 'who\'s', 'whom', 'why', 'why\'s', 'with', 'won\'t', 'would', 'wouldn\'t', 'you',
    'you\'d', 'you\'ll', 'you\'re', 'you\'ve', 'your', 'yours', 'yourself', 'yourselves'
}

DOMAIN_KEYWORDS = {
    'agent': 'agentic',
    'agents': 'agentic',
    'swarm': 'agentic',
    'mcp': 'agentic_protocol',
    'protocol': 'architecture',
    'runtime': 'architecture',
    'bigquery': 'data_platform',
    'sql': 'query_language',
    'googlesql': 'query_language',
    'etl': 'data_engineering',
    'pipeline': 'data_engineering',
    'power bi': 'bi_analytics',
    'looker': 'bi_analytics',
    'dbt': 'data_engineering',
    'dmbox': 'governance',
    'dama': 'governance',
    'governance': 'governance',
    'waas': 'business_model',
    'saas': 'business_model',
    'cert': 'education',
    'certification': 'education',
    'architect': 'architecture',
    'cloud': 'cloud_infra',
    'gcp': 'cloud_infra',
    'vertex': 'cloud_infra',
    'database': 'data_platform',
    'reflection': 'agentic_memory',
    'episodic': 'agentic_memory',
    'debate': 'orchestration',
    'topology': 'orchestration',
    'supervisor': 'orchestration'
}


class CommsVault:
    """
    SQLite Communication Vault and linguistic tracker for recording user conversations,
    analyzing understanding milestones, and modeling personal vocabulary style.
    """

    def __init__(self, db_path: Path | str = DEFAULT_DB_PATH) -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()

    @contextlib.contextmanager
    def get_connection(self) -> Iterator[sqlite3.Connection]:
        """Yield a connection that commits/rolls back and is always closed on exit."""
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON;")
            conn.execute("PRAGMA journal_mode = WAL;")
            with conn:
                yield conn
        finally:
            conn.close()

    def init_db(self) -> None:
        """Initialize relational schema, FTS5 index, and analytical views."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 1. Conversations / Sessions Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                conversation_id TEXT PRIMARY KEY,
                title TEXT,
                started_at TIMESTAMP,
                last_activity TIMESTAMP,
                total_messages INTEGER DEFAULT 0,
                user_messages INTEGER DEFAULT 0,
                agent_messages INTEGER DEFAULT 0,
                metadata JSON
            );
            """)

            # 2. Raw & Parsed Messages Table
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                step_index INTEGER NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                sender TEXT NOT NULL,          -- 'USER' or 'AGENT'
                role TEXT NOT NULL,            -- 'user' or 'assistant'
                clean_content TEXT NOT NULL,
                raw_payload TEXT,
                word_count INTEGER,
                char_count INTEGER,
                tokens_est INTEGER,
                UNIQUE(conversation_id, step_index, sender),
                FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id) ON DELETE CASCADE
            );
            """)

            # 3. User Vocabulary Ledger
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_vocabulary (
                term TEXT PRIMARY KEY,
                category TEXT DEFAULT 'general',
                first_used TIMESTAMP,
                last_used TIMESTAMP,
                frequency INTEGER DEFAULT 1,
                sample_context TEXT
            );
            """)

            # 4. User N-Gram Phrase Patterns (Bigrams & Trigrams)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_phrases (
                phrase TEXT PRIMARY KEY,
                n_length INTEGER NOT NULL,
                frequency INTEGER DEFAULT 1,
                first_used TIMESTAMP,
                last_used TIMESTAMP,
                sample_snippet TEXT
            );
            """)

            # 5. Understanding & Concept Progression
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS understanding_milestones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                message_id INTEGER NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                concept TEXT NOT NULL,
                depth_level TEXT NOT NULL,     -- 'Inquiry', 'Synthesis', 'Strategy', 'Execution'
                snippet TEXT NOT NULL,
                FOREIGN KEY (conversation_id) REFERENCES conversations(conversation_id),
                FOREIGN KEY (message_id) REFERENCES messages(id)
            );
            """)

            # 6. Daily Engagement Aggregates
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_engagement (
                date TEXT PRIMARY KEY,
                user_messages INTEGER DEFAULT 0,
                agent_messages INTEGER DEFAULT 0,
                user_words INTEGER DEFAULT 0,
                active_conversations INTEGER DEFAULT 0,
                topics_summary TEXT
            );
            """)

            # 7. Full-Text Search (FTS5) for fast conversational recall
            cursor.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS messages_fts USING fts5(
                content,
                conversation_id UNINDEXED,
                sender UNINDEXED,
                tokenize = 'porter unicode61'
            );
            """)

            # 8. Analytical Views
            cursor.execute("""
            CREATE VIEW IF NOT EXISTS v_top_vocabulary AS
            SELECT 
                term,
                category,
                frequency,
                first_used,
                last_used,
                sample_context
            FROM user_vocabulary
            ORDER BY frequency DESC;
            """)

            cursor.execute("""
            CREATE VIEW IF NOT EXISTS v_daily_activity AS
            SELECT 
                strftime('%Y-%m-%d', timestamp) AS activity_date,
                SUM(CASE WHEN sender = 'USER' THEN 1 ELSE 0 END) AS user_turns,
                SUM(CASE WHEN sender = 'AGENT' THEN 1 ELSE 0 END) AS agent_turns,
                SUM(CASE WHEN sender = 'USER' THEN word_count ELSE 0 END) AS user_words_written
            FROM messages
            GROUP BY strftime('%Y-%m-%d', timestamp)
            ORDER BY activity_date DESC;
            """)

            cursor.execute("""
            CREATE VIEW IF NOT EXISTS v_understanding_summary AS
            SELECT 
                concept,
                depth_level,
                COUNT(*) AS touchpoints,
                MIN(timestamp) AS first_explored,
                MAX(timestamp) AS latest_explored
            FROM understanding_milestones
            GROUP BY concept, depth_level
            ORDER BY touchpoints DESC;
            """)

            conn.commit()

    # -------------------------------------------------------------------------
    # Ingestion & Parsing
    # -------------------------------------------------------------------------

    @staticmethod
    def _clean_user_content(raw_text: str) -> str:
        """Extract clean user text from XML metadata wrappers like <USER_REQUEST>."""
        if not raw_text:
            return ""
        match = re.search(r"<USER_REQUEST>\s*(.*?)\s*</USER_REQUEST>", raw_text, re.DOTALL)
        if match:
            return match.group(1).strip()
        # Fallback: remove XML-like tags
        cleaned = re.sub(r"<[A-Z_]+>.*?</[A-Z_]+>", "", raw_text, flags=re.DOTALL)
        return cleaned.strip() or raw_text.strip()

    def record_message(
        self,
        conversation_id: str,
        step_index: int,
        timestamp: str,
        sender: str,
        role: str,
        content: str,
        raw_payload: Optional[str] = None
    ) -> int:
        """Insert or update a message, update engagement, and extract vocabulary."""
        clean = self._clean_user_content(content) if sender == "USER" else content.strip()
        words = re.findall(r"\b[\w'-]+\b", clean)
        word_count = len(words)
        char_count = len(clean)
        tokens_est = int(word_count * 1.33)

        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Ensure conversation exists
            cursor.execute("""
            INSERT INTO conversations (conversation_id, title, started_at, last_activity)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(conversation_id) DO UPDATE SET
                last_activity = excluded.last_activity;
            """, (conversation_id, f"Session {conversation_id[:8]}", timestamp, timestamp))

            # Insert message safely with ON CONFLICT DO UPDATE
            cursor.execute("""
            INSERT INTO messages (
                conversation_id, step_index, timestamp, sender, role,
                clean_content, raw_payload, word_count, char_count, tokens_est
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(conversation_id, step_index, sender) DO UPDATE SET
                clean_content = excluded.clean_content,
                raw_payload = excluded.raw_payload,
                word_count = excluded.word_count,
                char_count = excluded.char_count,
                tokens_est = excluded.tokens_est;
            """, (conversation_id, step_index, timestamp, sender, role, clean, raw_payload, word_count, char_count, tokens_est))
            
            cursor.execute(
                "SELECT id FROM messages WHERE conversation_id = ? AND step_index = ? AND sender = ?;",
                (conversation_id, step_index, sender)
            )
            row = cursor.fetchone()
            message_id = row[0] if row else 0

            # Update conversation counts
            cursor.execute("""
            UPDATE conversations SET
                total_messages = (SELECT COUNT(*) FROM messages WHERE conversation_id = ?),
                user_messages = (SELECT COUNT(*) FROM messages WHERE conversation_id = ? AND sender = 'USER'),
                agent_messages = (SELECT COUNT(*) FROM messages WHERE conversation_id = ? AND sender = 'AGENT'),
                last_activity = ?
            WHERE conversation_id = ?;
            """, (conversation_id, conversation_id, conversation_id, timestamp, conversation_id))

            # Add to FTS if not present
            cursor.execute("""
            DELETE FROM messages_fts WHERE conversation_id = ? AND rowid = ?;
            """, (conversation_id, message_id))
            cursor.execute("""
            INSERT INTO messages_fts (rowid, content, conversation_id, sender)
            VALUES (?, ?, ?, ?);
            """, (message_id, clean, conversation_id, sender))

            # Process User Vocabulary & Understanding if from User
            if sender == "USER" and clean:
                self._process_user_linguistics(cursor, clean, timestamp, conversation_id, message_id)

            conn.commit()
            return message_id

    def _process_user_linguistics(
        self,
        cursor: sqlite3.Cursor,
        text: str,
        timestamp: str,
        conversation_id: str,
        message_id: int
    ) -> None:
        """Extract vocabulary terms, n-grams, and concepts from user prompt."""
        clean_text = text.lower()
        tokens = re.findall(r"\b[a-z0-9_-]+\b", clean_text)

        # 1. Single Terms
        for term in tokens:
            if len(term) < 2 or term in STOPWORDS:
                continue

            category = DOMAIN_KEYWORDS.get(term, 'general')
            # Extract a 10-word snippet containing the term
            match = re.search(rf"([^.\n]*?\b{re.escape(term)}\b[^.\n]*)", text, re.IGNORECASE)
            snippet = match.group(1).strip()[:160] if match else text[:120]

            cursor.execute("""
            INSERT INTO user_vocabulary (term, category, first_used, last_used, frequency, sample_context)
            VALUES (?, ?, ?, ?, 1, ?)
            ON CONFLICT(term) DO UPDATE SET
                frequency = frequency + 1,
                last_used = excluded.last_used,
                category = CASE WHEN excluded.category != 'general' THEN excluded.category ELSE user_vocabulary.category END,
                sample_context = excluded.sample_context;
            """, (term, category, timestamp, timestamp, snippet))

        # 2. Bigrams / Trigrams
        for n in (2, 3):
            for i in range(len(tokens) - n + 1):
                gram = tokens[i : i + n]
                if any(t in STOPWORDS for t in (gram[0], gram[-1])):
                    continue  # Skip if starts or ends with stopword
                phrase = " ".join(gram)
                snippet = text[:140]

                cursor.execute("""
                INSERT INTO user_phrases (phrase, n_length, frequency, first_used, last_used, sample_snippet)
                VALUES (?, ?, 1, ?, ?, ?)
                ON CONFLICT(phrase) DO UPDATE SET
                    frequency = frequency + 1,
                    last_used = excluded.last_used;
                """, (phrase, n, timestamp, timestamp, snippet))

        # 3. Detect Understanding Milestones
        self._detect_understanding_milestones(cursor, text, timestamp, conversation_id, message_id)

    def _detect_understanding_milestones(
        self,
        cursor: sqlite3.Cursor,
        text: str,
        timestamp: str,
        conversation_id: str,
        message_id: int
    ) -> None:
        """Classify user comprehension level based on phrasing and domain topics."""
        lower = text.lower()

        # Topic detection
        detected_topics = []
        for kw, cat in DOMAIN_KEYWORDS.items():
            if kw in lower:
                detected_topics.append((kw.upper(), cat))

        # Phrasing depth detection
        depth = "Inquiry"
        if any(w in lower for w in ["how does", "what is", "where do i start", "why does"]):
            depth = "Inquiry"
        elif any(w in lower for w in ["i like your thinking", "i see how", "putting all this", "feed all of this"]):
            depth = "Synthesis"
        elif any(w in lower for w in ["the ultimate plan", "i want to start", "my niche", "position myself", "build products"]):
            depth = "Strategy"
        elif any(w in lower for w in ["create a sql database", "record everything", "save this cv", "build my own"]):
            depth = "Execution"

        for topic, _ in detected_topics[:3]:  # Top 3 topics
            cursor.execute("""
            INSERT INTO understanding_milestones (
                conversation_id, message_id, timestamp, concept, depth_level, snippet
            ) VALUES (?, ?, ?, ?, ?, ?);
            """, (conversation_id, message_id, timestamp, topic, depth, text[:200]))

    def sync_brain_transcripts(self, brain_dir: Path | str = DEFAULT_BRAIN_DIR) -> Dict[str, int]:
        """
        Scans all Antigravity conversation directories and ingests complete message histories
        into the SQLite vault.
        """
        brain_path = Path(brain_dir)
        stats = {"conversations_scanned": 0, "messages_ingested": 0}

        if not brain_path.exists():
            return stats

        for conv_dir in sorted(brain_path.iterdir()):
            if not conv_dir.is_dir() or conv_dir.name == "tempmediaStorage":
                continue

            transcript_file = conv_dir / ".system_generated" / "logs" / "transcript.jsonl"
            if not transcript_file.exists():
                continue

            stats["conversations_scanned"] += 1
            conv_id = conv_dir.name

            try:
                with open(transcript_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            record = json.loads(line)
                        except json.JSONDecodeError:
                            continue

                        step_idx = record.get("step_index", 0)
                        created_at = record.get("created_at") or datetime.now(timezone.utc).isoformat()
                        rec_type = record.get("type", "")
                        source = record.get("source", "")
                        content = record.get("content", "")

                        if rec_type == "USER_INPUT" and source == "USER_EXPLICIT":
                            self.record_message(
                                conversation_id=conv_id,
                                step_index=step_idx,
                                timestamp=created_at,
                                sender="USER",
                                role="user",
                                content=content,
                                raw_payload=line
                            )
                            stats["messages_ingested"] += 1

                        elif rec_type == "PLANNER_RESPONSE" and source == "MODEL" and content:
                            self.record_message(
                                conversation_id=conv_id,
                                step_index=step_idx,
                                timestamp=created_at,
                                sender="AGENT",
                                role="assistant",
                                content=content,
                                raw_payload=line
                            )
                            stats["messages_ingested"] += 1

            except Exception as e:
                print(f"[CommsVault] Error processing {transcript_file}: {e}")

        return stats

    # -------------------------------------------------------------------------
    # Analytical & Agentic Persona Query APIs
    # -------------------------------------------------------------------------

    def get_user_profile_summary(self) -> Dict[str, Any]:
        """Provides an AI agent with an analytical profile of Mpho's vocabulary and cadence."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Message aggregates
            cursor.execute("""
            SELECT 
                COUNT(*) AS total_turns,
                SUM(word_count) AS total_words,
                AVG(word_count) AS avg_words_per_turn
            FROM messages WHERE sender = 'USER';
            """)
            msg_stats = dict(cursor.fetchone() or {})

            # Top vocabulary
            cursor.execute("""
            SELECT term, frequency, category, sample_context
            FROM user_vocabulary
            ORDER BY frequency DESC
            LIMIT 25;
            """)
            top_vocab = [dict(row) for row in cursor.fetchall()]

            # Top recurring phrases
            cursor.execute("""
            SELECT phrase, frequency, sample_snippet
            FROM user_phrases
            ORDER BY frequency DESC
            LIMIT 15;
            """)
            top_phrases = [dict(row) for row in cursor.fetchall()]

            # Understanding milestones breakdown
            cursor.execute("""
            SELECT concept, depth_level, COUNT(*) as count
            FROM understanding_milestones
            GROUP BY concept, depth_level
            ORDER BY count DESC
            LIMIT 15;
            """)
            milestones = [dict(row) for row in cursor.fetchall()]

            return {
                "user_name": "Mpho Mashile",
                "system_alias": "Acinonyx",
                "communication_metrics": msg_stats,
                "frequent_vocabulary": top_vocab,
                "recurring_phrases": top_phrases,
                "comprehension_trajectory": milestones
            }

    def search_comms(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Fast full-text search across all previous chats."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            SELECT 
                m.id,
                m.conversation_id,
                m.timestamp,
                m.sender,
                m.clean_content
            FROM messages_fts f
            JOIN messages m ON f.rowid = m.id
            WHERE messages_fts MATCH ?
            ORDER BY m.timestamp DESC
            LIMIT ?;
            """, (query, limit))
            return [dict(row) for row in cursor.fetchall()]


if __name__ == "__main__":
    vault = CommsVault()
    print(f"[*] Initialized CommsVault at {DEFAULT_DB_PATH}")
    stats = vault.sync_brain_transcripts()
    print(f"[+] Ingestion complete: {stats}")
    profile = vault.get_user_profile_summary()
    print(f"[+] Total User Words Captured: {profile['communication_metrics']['total_words']}")
    print(f"[+] Top Terms: {[v['term'] for v in profile['frequent_vocabulary'][:10]]}")
