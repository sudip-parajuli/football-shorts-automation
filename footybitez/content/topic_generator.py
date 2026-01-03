import random
import os

class TopicGenerator:
    def __init__(self):
        self.used_topics_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "used_topics.json")
        os.makedirs(os.path.dirname(self.used_topics_file), exist_ok=True)
        
        self.topics = [
            "Lionel Messi's 91 goal year",
            "Cristiano Ronaldo's jumping height",
            "Leicester City's 2016 Premier League win",
            "Pele's 3 World Cups",
            "Zinedine Zidane's 2006 headbutt",
            "The fastest goal in World Cup history",
            "Lewandowski's 5 goals in 9 minutes",
            "Arsenal's Invincibles season",
            "Maradona's Hand of God",
            "Real Madrid's 3-peat Champions League",
            "Neymar's world record transfer",
            "Andres Iniesta's 2010 World Cup winner",
            "The originals rules of football",
            "Why Brazil wears yellow",
            "The highest attendance in a football match",
            "Rogerio Ceni: The goalscoring goalkeeper",
            "Just Fontaine's 13 goals in one World Cup",
            "Nottingham Forest winning back-to-back UCL",
            "Greece winning Euro 2004",
            "Denmark winning Euro 1992",
            "Luis Suarez biting incidents",
            "The story of the Jules Rimet Trophy",
            "Why football balls have honeycombs",
            "The first ever World Cup in 1930",
            "Miroslav Klose's World Cup record",
            "Ali Daei's international goal record",
            "Sadio Mane's fastest hat-trick",
            "Jose Mourinho's home unbeaten run",
            "Fergie Time",
            "The 'Aguerrooooo' moment",
            "Zlatan Ibrahimovic's bicycle kick vs England",
            "Roberto Carlos' free kick vs France",
            "Dennis Bergkamp's turn vs Newcastle",
            "Thierry Henry's handball vs Ireland",
            "Germany 7-1 Brazil",
            "Iceland's thunder clap",
            "South Korea's 2002 World Cup run",
            "James Rodriguez 2014 World Cup volley",
            "Ronaldo Nazario's haircut 2002",
            "David Beckham's halfway line goal",
            "Eric Cantona's kung fu kick",
            "Liverpool's comeback in Istanbul 2005",
            "Man Utd 1999 Treble",
            "Barcelona's Tiki Taka era",
            "Total Football by Netherlands",
            "Garrincha: The angel with bent legs",
            "Lev Yashin: The Black Spider",
            "Ferenc Puskas",
            "George Best",
            "Johan Cruyff"
        ]

    def _load_used_topics(self):
        """Loads the set of used topics from JSON."""
        if not os.path.exists(self.used_topics_file):
            return set()
        try:
            import json
            with open(self.used_topics_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return set(t.lower() for t in data)
        except Exception as e:
            print(f"Warning: Failed to load used topics: {e}")
            return set()

    def mark_topic_as_used(self, topic):
        """Adds a topic to the used list and persists it."""
        try:
            import json
            used = self._load_used_topics()
            used.add(topic.lower())
            
            with open(self.used_topics_file, 'w', encoding='utf-8') as f:
                json.dump(list(used), f, indent=2)
        except Exception as e:
            print(f"Error saving used topic: {e}")

    def get_random_topic(self):
        """Selects a random topic from the list that hasn't been used yet."""
        used_topics = self._load_used_topics()
        
        # Filter available topics
        available_topics = [t for t in self.topics if t.lower() not in used_topics]
        
        if not available_topics:
            print("Warning: All topics have been covered! Resetting or recycling...")
            return random.choice(self.topics)
            
        return random.choice(available_topics)

if __name__ == "__main__":
    generator = TopicGenerator()
    print(f"Selected Topic: {generator.get_random_topic()}")
