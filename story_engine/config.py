"""
This file contains the configuration for the story engine. The story needs to be creative so I set a higher temperature for the 
story generation. The judge is more strict so I set a lower temperature for the judge. The revision needs to be a balance between 
creative and strict so I set it as 0.5. Refinement rounds are limited to 3 to avoid infinite loops.
The number of decisions is set to 2 to avoid too many choices.
"""

MAX_TOKENS = 500

STORY_TEMPERATURE = 0.7
JUDGE_TEMPERATURE = 0.1
REVISION_TEMPERATURE = 0.5

MAX_REFINEMENT_ROUNDS = 3

NUMBER_OF_DECISIONS = 2
