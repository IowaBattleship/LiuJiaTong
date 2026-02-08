# Game Rules (LiuJiaTong / 六家通)

## 1. Basic Rules

- At the start of the game, the system deals cards. Each player receives **36 cards**.
- During the game, players try to score points and be the first to play out all their cards.
- The game ends when:
  - Only one player has cards left, or
  - One side has played out all their cards.
- Final scores are calculated based on points won by each side.

## 2. Scoring Cards

- **5** = 5 points  
- **10** = 10 points  
- **K** = 10 points  

- In each round, the player who plays the strongest combination wins all scoring cards (5, 10, K) played in that round.

## 3. Card Types

### 3.1 Single
- Any single card.

### 3.2 Pair
- Two cards of the same rank, regardless of suit.

### 3.3 Straight Pairs (Consecutive Pairs)
- Two or more consecutive pairs, e.g. 4455, 445566.
- **AA22** is allowed (minimum straight pairs).
- **AA223344...KKAA** is **not** allowed (A cannot wrap around both ends).
- When A is used as low, it counts as 1 (e.g. A2345). When A is used as high, it counts as A (e.g. ...KAA).

### 3.4 Triple
- Three cards of the same rank, regardless of suit.

### 3.5 Straight Triples (Consecutive Triples)
- Two or more consecutive triples, e.g. 333444, 444555666.
- **AAA222** and **AAA222333** are allowed.

### 3.6 Flight (Butterfly)
- Straight triples with matching consecutive pairs attached.
- Example: 444555666JJQQKK; AAA222333JJQQKK.
- **AAAKKKQQQ3322AA** can be interpreted as a valid Flight.
- Size is determined by the straight triples part.

### 3.7 Straight
- Exactly **five** consecutive cards, e.g. 45678.
- **A2345** is allowed (A as 1).

### 3.8 Three with a Pair (Triple Pair)
- Three of a kind plus a pair (5 cards total).
- Example: AAA + BB.

### 3.9 Bomb
- Four or more cards of the same rank, e.g. 4444, 55555.

## 4. Jokers (Wild Cards)

- Both **Big Joker** and **Small Joker** act as wild cards (财神).
- A Joker can substitute any card to form a valid combination.
- Example: Big Joker + 222 = 2222.
- Big Joker and Small Joker **cannot** substitute for each other.
- Special case: **888 + Small Joker + Small Joker** = bomb of five 8s (not triple with jokers).

## 5. Card Rank (Highest to Lowest)

- **Big Joker** > **Small Joker** > **2** > **A** > **K** > **Q** > **J** > **10** > **9** > **8** > **7** > **6** > **5** > **4** > **3**

## 6. Comparing Card Types

- **Pairs and Triples**: Compared by the rank of the main cards.
- **Straight Pairs, Straight Triples, Straights**: Compared by the highest card, provided the number of cards is the same. Different lengths cannot be compared.
- **Flight**: Compared by the straight triples part.
- **Bombs**: Compared by rank if they have the same number of cards; otherwise, more cards = stronger.
  - Bombs beat all non-bomb types.
  - **8×2** (eight 2s) < **4 Small Jokers** < **4 Big Jokers** < **9×3** (nine 3s).
- When used as wild cards, Big Joker and Small Joker do not differ in rank (e.g. 333+Big Joker = 333+Small Joker).

## 7. Playing Rules

- **First round**: The system randomly chooses one player to lead.
- **Later rounds**: The player who led in the previous round leads again.
- Six players take turns **counter-clockwise**.
- Each player must play a combination **stronger** than the previous one, or **pass**.
- If a player has no valid play or chooses not to play, they pass.
- If all other players pass, the last player who played may lead with a new combination.
- When a player plays their last hand and all others pass, the **next player** (counter-clockwise) leads.
- Jokers can substitute any card to form valid combinations, but Big Joker and Small Joker cannot substitute each other.
- Scoring cards (5, 10, K) played in a round are awarded to the player who wins that round.
