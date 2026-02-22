"""
ALD-01 Learning System
Tracks user patterns, preferences, and frequently used commands to improve over time.
Learns which agents, modes, and responses the user prefers.
"""

import os
import time
import json
import logging
from typing import Any, Dict, List, Optional
from collections import Counter, defaultdict
from dataclasses import dataclass, field

from ald01 import CONFIG_DIR

logger = logging.getLogger("ald01.learning")


@dataclass
class UserPattern:
    """A detected user behavior pattern."""
    pattern_type: str  # 'agent_preference', 'time_pattern', 'topic_frequency', 'mode_usage'
    key: str
    value: Any
    frequency: int = 0
    confidence: float = 0.0
    last_seen: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": self.pattern_type,
            "key": self.key,
            "value": self.value,
            "frequency": self.frequency,
            "confidence": round(self.confidence, 2),
            "last_seen": self.last_seen,
        }


class LearningSystem:
    """
    Learns from user interactions to improve ALD-01 over time.
    
    Tracks:
    - Agent usage patterns (which agents the user prefers)
    - Topic frequency (what the user asks about most)
    - Time-of-day patterns (when the user is most active)
    - Mode switching patterns
    - Response quality feedback (implicit from follow-ups)
    - Command frequency
    - Provider performance per user
    - Preferred response length
    """

    def __init__(self):
        self._persistence_path = os.path.join(CONFIG_DIR, "learning.json")
        self._agent_usage: Counter = Counter()
        self._topic_frequency: Counter = Counter()
        self._mode_usage: Counter = Counter()
        self._hour_activity: Counter = Counter()
        self._command_frequency: Counter = Counter()
        self._provider_latencies: Dict[str, List[float]] = defaultdict(list)
        self._response_lengths: List[int] = []
        self._query_lengths: List[int] = []
        self._follow_up_rate: float = 0.0
        self._total_interactions: int = 0
        self._session_start: float = time.time()
        self._feedback: List[Dict[str, Any]] = []
        self._patterns: List[UserPattern] = []
        self._load()

    def record_interaction(
        self,
        query: str,
        agent_used: str,
        provider_used: str,
        mode: str,
        response_length: int,
        latency_ms: float,
        was_follow_up: bool = False,
    ) -> None:
        """Record a complete interaction for learning."""
        self._total_interactions += 1

        # Agent usage
        self._agent_usage[agent_used] += 1

        # Topic keywords
        keywords = self._extract_keywords(query)
        for kw in keywords:
            self._topic_frequency[kw] += 1

        # Mode usage
        self._mode_usage[mode] += 1

        # Time patterns
        hour = time.localtime().tm_hour
        self._hour_activity[hour] += 1

        # Provider performance
        self._provider_latencies[provider_used].append(latency_ms)
        # Keep only last 100 latencies per provider
        if len(self._provider_latencies[provider_used]) > 100:
            self._provider_latencies[provider_used] = self._provider_latencies[provider_used][-100:]

        # Response lengths
        self._response_lengths.append(response_length)
        if len(self._response_lengths) > 500:
            self._response_lengths = self._response_lengths[-500:]

        # Query lengths
        self._query_lengths.append(len(query))
        if len(self._query_lengths) > 500:
            self._query_lengths = self._query_lengths[-500:]

        # Follow-up tracking
        if was_follow_up:
            total = max(self._total_interactions, 1)
            self._follow_up_rate = (self._follow_up_rate * (total - 1) + 1) / total

        # Auto-save periodically
        if self._total_interactions % 20 == 0:
            self._detect_patterns()
            self._save()

    def record_command(self, command: str) -> None:
        """Record a CLI command usage."""
        self._command_frequency[command] += 1

    def record_feedback(self, feedback_type: str, value: Any, context: str = "") -> None:
        """Record explicit user feedback."""
        self._feedback.append({
            "type": feedback_type,
            "value": value,
            "context": context,
            "timestamp": time.time(),
        })
        if len(self._feedback) > 200:
            self._feedback = self._feedback[-200:]

    def _extract_keywords(self, query: str) -> List[str]:
        """Extract meaningful keywords from a query."""
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
            "have", "has", "had", "do", "does", "did", "will", "would", "shall",
            "should", "may", "might", "can", "could", "i", "me", "my", "we",
            "you", "your", "he", "she", "it", "they", "them", "this", "that",
            "what", "which", "who", "whom", "how", "when", "where", "why",
            "in", "on", "at", "by", "for", "with", "to", "from", "of", "and",
            "or", "not", "no", "but", "if", "so", "as", "up", "out", "about",
            "into", "through", "during", "before", "after", "above", "below",
            "between", "all", "each", "every", "both", "few", "more", "most",
            "other", "some", "such", "than", "too", "very", "just", "also",
            "please", "help", "want", "need", "like", "make", "use", "get",
            "write", "create", "show", "tell", "give", "know", "think",
        }

        words = query.lower().split()
        keywords = [w.strip(".,?!:;\"'()[]{}") for w in words if len(w) > 2]
        keywords = [w for w in keywords if w and w not in stop_words]
        return keywords[:10]  # Limit to top 10

    def _detect_patterns(self) -> None:
        """Detect behavioral patterns from collected data."""
        self._patterns = []

        # Agent preference
        if self._agent_usage:
            top_agent = self._agent_usage.most_common(1)[0]
            total = sum(self._agent_usage.values())
            confidence = top_agent[1] / max(total, 1)
            if confidence > 0.3:
                self._patterns.append(UserPattern(
                    pattern_type="agent_preference",
                    key="preferred_agent",
                    value=top_agent[0],
                    frequency=top_agent[1],
                    confidence=confidence,
                ))

        # Top topics
        if self._topic_frequency:
            for topic, count in self._topic_frequency.most_common(5):
                if count >= 3:
                    self._patterns.append(UserPattern(
                        pattern_type="topic_frequency",
                        key=topic,
                        value=count,
                        frequency=count,
                        confidence=min(count / 10, 1.0),
                    ))

        # Peak hours
        if self._hour_activity:
            peak_hour = self._hour_activity.most_common(1)[0]
            self._patterns.append(UserPattern(
                pattern_type="time_pattern",
                key="peak_hour",
                value=peak_hour[0],
                frequency=peak_hour[1],
                confidence=peak_hour[1] / max(sum(self._hour_activity.values()), 1),
            ))

        # Preferred mode
        if self._mode_usage:
            top_mode = self._mode_usage.most_common(1)[0]
            total = sum(self._mode_usage.values())
            if top_mode[1] > 2:
                self._patterns.append(UserPattern(
                    pattern_type="mode_usage",
                    key="preferred_mode",
                    value=top_mode[0],
                    frequency=top_mode[1],
                    confidence=top_mode[1] / max(total, 1),
                ))

        # Average query complexity
        if self._query_lengths:
            avg_len = sum(self._query_lengths) / len(self._query_lengths)
            self._patterns.append(UserPattern(
                pattern_type="query_complexity",
                key="avg_query_length",
                value=round(avg_len),
                frequency=len(self._query_lengths),
                confidence=0.8 if len(self._query_lengths) > 10 else 0.3,
            ))

    def get_recommendations(self) -> List[Dict[str, str]]:
        """Get personalized recommendations based on learned patterns."""
        recommendations = []

        for pattern in self._patterns:
            if pattern.pattern_type == "agent_preference" and pattern.confidence > 0.5:
                recommendations.append({
                    "type": "agent",
                    "message": f"You frequently use the {pattern.value} agent. Consider setting it as your default with: ald-01 config set default_agent {pattern.value}",
                })

            if pattern.pattern_type == "topic_frequency" and pattern.frequency >= 5:
                recommendations.append({
                    "type": "topic",
                    "message": f"You ask about '{pattern.key}' often. Try switching to a specialized mode for better results.",
                })

            if pattern.pattern_type == "mode_usage" and pattern.confidence > 0.6:
                recommendations.append({
                    "type": "mode",
                    "message": f"You prefer {pattern.value} mode. Consider setting it as your default mode.",
                })

        # Provider speed recommendation
        if self._provider_latencies:
            fastest = min(
                self._provider_latencies.items(),
                key=lambda x: sum(x[1]) / max(len(x[1]), 1),
            )
            avg_ms = sum(fastest[1]) / max(len(fastest[1]), 1)
            recommendations.append({
                "type": "provider",
                "message": f"Fastest provider for you: {fastest[0]} (avg {avg_ms:.0f}ms). Set as primary for speed.",
            })

        return recommendations

    def get_preferred_agent(self) -> Optional[str]:
        """Get the user's most-used agent."""
        if self._agent_usage:
            return self._agent_usage.most_common(1)[0][0]
        return None

    def get_preferred_mode(self) -> Optional[str]:
        """Get the user's most-used mode."""
        if self._mode_usage:
            return self._mode_usage.most_common(1)[0][0]
        return None

    def get_provider_ranking(self) -> List[Dict[str, Any]]:
        """Rank providers by speed based on user's experience."""
        ranking = []
        for provider, latencies in self._provider_latencies.items():
            if latencies:
                avg = sum(latencies) / len(latencies)
                ranking.append({
                    "provider": provider,
                    "avg_latency_ms": round(avg),
                    "samples": len(latencies),
                    "min_ms": round(min(latencies)),
                    "max_ms": round(max(latencies)),
                })
        ranking.sort(key=lambda x: x["avg_latency_ms"])
        return ranking

    def get_stats(self) -> Dict[str, Any]:
        """Get learning system statistics."""
        return {
            "total_interactions": self._total_interactions,
            "top_agents": dict(self._agent_usage.most_common(5)),
            "top_topics": dict(self._topic_frequency.most_common(10)),
            "top_modes": dict(self._mode_usage.most_common(5)),
            "top_commands": dict(self._command_frequency.most_common(10)),
            "peak_hours": dict(self._hour_activity.most_common(3)),
            "patterns_detected": len(self._patterns),
            "avg_query_length": round(sum(self._query_lengths) / max(len(self._query_lengths), 1)),
            "avg_response_length": round(sum(self._response_lengths) / max(len(self._response_lengths), 1)),
            "follow_up_rate": round(self._follow_up_rate, 2),
            "provider_ranking": self.get_provider_ranking(),
        }

    def get_patterns(self) -> List[Dict[str, Any]]:
        """Get detected patterns."""
        self._detect_patterns()
        return [p.to_dict() for p in self._patterns]

    # ──────────────────────────────────────────────────────────
    # Persistence
    # ──────────────────────────────────────────────────────────

    def _save(self) -> None:
        """Save learning data."""
        try:
            data = {
                "total_interactions": self._total_interactions,
                "agent_usage": dict(self._agent_usage),
                "topic_frequency": dict(self._topic_frequency.most_common(100)),
                "mode_usage": dict(self._mode_usage),
                "hour_activity": {str(k): v for k, v in self._hour_activity.items()},
                "command_frequency": dict(self._command_frequency.most_common(50)),
                "provider_latencies": {
                    k: v[-50:] for k, v in self._provider_latencies.items()
                },
                "follow_up_rate": self._follow_up_rate,
                "feedback": self._feedback[-50:],
                "saved_at": time.time(),
            }
            os.makedirs(os.path.dirname(self._persistence_path), exist_ok=True)
            with open(self._persistence_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save learning data: {e}")

    def _load(self) -> None:
        """Load learning data."""
        try:
            if os.path.exists(self._persistence_path):
                with open(self._persistence_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                self._total_interactions = data.get("total_interactions", 0)
                self._agent_usage = Counter(data.get("agent_usage", {}))
                self._topic_frequency = Counter(dict(data.get("topic_frequency", {})))
                self._mode_usage = Counter(data.get("mode_usage", {}))
                self._hour_activity = Counter({int(k): v for k, v in data.get("hour_activity", {}).items()})
                self._command_frequency = Counter(data.get("command_frequency", {}))
                self._follow_up_rate = data.get("follow_up_rate", 0.0)
                self._feedback = data.get("feedback", [])

                for provider, latencies in data.get("provider_latencies", {}).items():
                    self._provider_latencies[provider] = latencies

        except Exception as e:
            logger.warning(f"Failed to load learning data: {e}")


# Singleton
_learning_system: Optional[LearningSystem] = None


def get_learning_system() -> LearningSystem:
    """Get or create the global learning system."""
    global _learning_system
    if _learning_system is None:
        _learning_system = LearningSystem()
    return _learning_system
