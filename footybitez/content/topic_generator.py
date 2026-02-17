import random
import os
import json

class TopicGenerator:
    def __init__(self):
        self.used_topics_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "used_topics.json")
        os.makedirs(os.path.dirname(self.used_topics_file), exist_ok=True)
        
        # Define categories and their specific topics
        self.categories = {
            "Football Stories": [
                "The rise and fall of Ronaldinho",
                "How Leicester City won the impossible title",
                "The tragic career of Adriano",
                "The day football changed forever",
                "Jamie Vardy's rise from non-league",
                "The miracle of Istanbul 2005",
                "Zlatan Ibrahimovic's journey",
                "Didier Drogba stopping a civil war"
            ],
            "Mysteries & Dark Side": [
                "The strangest match ever played",
                "Footballers who disappeared",
                "The biggest scandals in football history",
                "Matches that were fixed",
                "The curse of Bela Guttmann",
                "Ronaldo's 1998 World Cup final mystery",
                "The darker side of the Qatar World Cup"
            ],
            "Comparisons & Debates": [
                "Messi vs Ronaldo: who really won more?",
                "Prime Neymar vs Prime Ronaldinho",
                "Best World Cup team ever?",
                "Top 5 most clutch players",
                "Is Haaland better than Mbappe?",
                "Pelé vs Maradona: The ultimate debate",
                "Premier League vs La Liga: Which is harder?"
            ],
            "What If?": [
                "What if Neymar never left Barcelona?",
                "What if Messi joined Chelsea?",
                "What if VAR existed in 1990?",
                "What if Brazil didn’t lose 7–1?",
                "What if Cristiano Ronaldo stayed at Man Utd (2009)?",
                "What if Lewandowski joined Blackburn Rovers?"
            ],
            "Tactics & IQ": [
                "Why Pep Guardiola changed football",
                "How tiki-taka really works",
                "Why parking the bus works",
                "The most dangerous counterattack ever",
                "The role of the False 9 explained",
                "Gegenpressing explained simply"
            ],
            "World Cup & Stats": [
                "History of the FIFA World Cup",
                "Total cost of hosting the World Cup by country",
                "Top 5 highest attendance in football history",
                "The future of the FIFA World Cup (48 teams)",
                "Who will host the next World Cups?",
                "The most expensive World Cup ever (Qatar)",
                "Evolution of the World Cup Trophy"
            ],
            "Shocking Moments": [
            	"The goal that shocked the world",
                "The worst miss in football history",
                "The most disrespectful celebration ever",
                "When a goalkeeper scored from 100 meters",
                "Zidane's headbutt in 2006",
                "Suarez's bite at the 2014 World Cup"
            ],
            "Money & Transfers": [
                "The most expensive mistake in football",
                "Transfers that destroyed careers",
                "Why PSG failed despite billions",
                "How agents control football",
                "The Neymar transfer that broke the market",
                "Chelsea's billion pound squad"
            ],
            "Referees, Rules & Weird Laws": [
                "Goals that shouldn’t have counted",
                "Strangest red cards ever",
                "Rules you didn’t know exist",
                "When referees decided championships",
                "The story of the first ever red card",
                "Why goalkeepers can't pick up backpasses"
            ],
            "Rankings & Lists": [
                "Top 10 one-season wonders",
                "Top 5 greatest comebacks",
                "Top 7 fastest goals",
                "Top 10 dirtiest players",
                "Top 5 goalkeepers of all time",
                "The most decorated players in history"
            ],
            "Psychology & Mental Side": [
                "Why players choke in finals",
                "How pressure destroys talent",
                "Why penalties are psychological",
                "Why home fans matter",
                "The psychology of a captain",
                "How confidence affects goalscoring"
            ],
            "Football Explained Simply": [
                "Why offsides exist",
                "Why goalkeepers wear gloves",
                "Why kits change every season",
                "Why football has 11 players",
                "How transfer fees work",
                "How the offside rule has changed"
            ],
            "Rivalries & Wars": [
                "El Clasico: more than football",
                "Why Boca vs River is dangerous",
                "The deadliest rivalry match",
                "Derbies that started riots",
                "Celtic vs Rangers: The Old Firm",
                "Manchester United vs Liverpool hate"
            ]
        }
        
        # Flatten for legacy support or random "any" selection
        self.all_topics = []
        for cat_topics in self.categories.values():
            self.all_topics.extend(cat_topics)

    def _load_used_topics(self):
        """Loads the set of used topics from JSON."""
        if not os.path.exists(self.used_topics_file):
            return set()
        try:
            with open(self.used_topics_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return set(t.lower() for t in data)
        except Exception as e:
            print(f"Warning: Failed to load used topics: {e}")
            return set()

    def mark_topic_as_used(self, topic):
        """Adds a topic to the used list and persists it."""
        try:
            used = self._load_used_topics()
            used.add(topic.lower())
            
            with open(self.used_topics_file, 'w', encoding='utf-8') as f:
                json.dump(list(used), f, indent=2)
        except Exception as e:
            print(f"Error saving used topic: {e}")

    def get_random_topic(self, category=None):
        """
        Selects a random topic.
        If category is provided, selects from that category.
        Otherwise, selects a random category first.
        """
        used_topics = self._load_used_topics()
        
        # Select Category
        if not category:
            category = random.choice(list(self.categories.keys()))
            
        print(f"Selected Category: {category}")
        
        possible_topics = self.categories.get(category, self.all_topics)
        
        # Filter available topics
        available_topics = [t for t in possible_topics if t.lower() not in used_topics]
        
        if not available_topics:
            print(f"Warning: All topics in {category} coverered! Recycling...")
            return random.choice(possible_topics), category
            
        return random.choice(available_topics), category

if __name__ == "__main__":
    generator = TopicGenerator()
    topic, cat = generator.get_random_topic()
    print(f"Category: {cat}\nTopic: {topic}")
