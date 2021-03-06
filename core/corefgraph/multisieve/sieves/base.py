# coding=utf-8
""" This is where the base of the sieves lives

"""

__author__ = 'Josu Bermudez <josu.bermudez@deusto.es>'


from ...graph.kafx import SyntacticTreeUtils
from ...graph.xutils import GraphWrapper
from ...features.grendel import GenderNumberExtractor
from ...resources.dictionaries import pronouns, stopwords
from ...resources.tagset import ner_tags
from logging import getLogger


class Sieve(object):
    """ The base of all the sieves of the system. It contains all the check, resolve and merge basic mechanics and also
     the methods to extract information from entities and candidates.

    """
    sort_name = "XXX"
    #Filter options
    ONLY_FIRST_MENTION = True
    NO_PRONOUN = True
    DISCOURSE_SALIENCE = True
    NO_STOP_WORDS = False

    unknown_array = [GenderNumberExtractor.UNKNOWN, ner_tags.no_ner, ner_tags.other]
    UNKNOWN = set(x for x in unknown_array)

    def __init__(self, multi_sieve_processor, options):
        self.logger = getLogger("sieves")
        self.multi_sieve_processor = multi_sieve_processor
        self.graph = self.multi_sieve_processor.graph
        self.graph_builder = GraphWrapper.get_graph_property(self.graph, "graph_builder")
        self.options = options
        self.tree_utils = SyntacticTreeUtils(graph=self.graph)
        self.discourse = "NO_DISCOURSE_SALIENCE" not in options
        self.clusters = []

    def are_coreferent(self, entity, mention, candidate):
        """ Determine if the candidate is a valid entity coreferent.
        :param candidate: The candidate that may corefer the entity.
        :param mention: The selected mention to represent the entity.
        :param entity: The entity that is going to be evaluated.
        """
        if candidate["id"] in entity:
            self.debug("LINK FILTERED already linked. Candidate: -%s-",
                       candidate['form'])
            return False
        if candidate["generic"] and self.is_you(candidate):
            self.debug("LINK FILTERED Generic Candidate. Candidate: -%s-",
                       candidate['form'])
            return False
        if(mention["form"].lower() == "this") and (self.graph_builder.sentence_distance(mention, candidate) > 3):
            self.debug("LINK FILTERED too far this. Candidate: -%s-",
                       candidate['form'])
            return False
        if self.graph_builder.is_inside(mention["span"],  candidate["span"]) or \
                self.graph_builder.is_inside(candidate["span"], mention["span"]):
            self.debug("LINK FILTERED Inside. Candidate: -%s-",
                       candidate['form'])
            return False
        return True

    def valid_mention(self, entity):
        """Look up in the entity for the first valid mention. In no one is founded return None.
        :param entity: The entity that is going to be examined.
        """
        mentions = []
        mention_index = 0
        for mention in entity:
            if self.validate(self.graph.node[mention], mention_index=mention_index):
                mention_index += 1
                mentions.append(mention)
        return mentions

    def validate(self, mention, mention_index):
        """ Determine if the mention is valid for this sieve.

        :param mention: The mention to check.
        :param mention_index: Index of the mention inside entity:
        """
        # Filter all no first mentions
        if self.ONLY_FIRST_MENTION and mention_index > 0:
            self.debug("MENTION FILTERED Not first one: %s", mention["form"])
            return False
        if self.NO_PRONOUN and self.is_pronoun(mention):
            self.debug("MENTION FILTERED Is a pronoun: %s", mention["form"])
            return False
        # Filter Narrative you
        if self.narrative_you(mention=mention):
            self.debug("MENTION FILTERED is a narrative you: %s", mention["form"])
            return False
        # filter generics
        if mention["generic"]:
            self.debug("MENTION FILTERED is generic: %s", mention["form"])
            return False
        # Filter stopWords
        if self.NO_STOP_WORDS and mention["form"].lower() in stopwords.stop_words:
            self.debug("MENTION FILTERED is a stop word: %s", mention["form"])
            return False
        if self.DISCOURSE_SALIENCE:
            # Filter indefinites
            if self.is_undefined(mention):
                self.debug("MENTION FILTERED is undefined: %s", mention["form"])
                return False
            # Filter if start with indefinite article and not in a construction
            if not mention["appositive"] and not mention["predicative_nominative"] and \
                    mention["started_by_undefined_mention"]:
                self.debug("MENTION FILTERED starts with undefined: %s", mention["form"])
                return False
        return True

    def merge(self, clusters, registers):
        """ Merge the cluster in a transitive function.
        Start for the first text appearance cluster(determined by his first mention)
        and merge entities but maintains the first cluster candidates.
        :param clusters: The list of pair entity candidatures that conform a text coreference proposal.
        :param registers: The list of strings that keep the record of merges that suffers a cluster.
        """

        index = 0
        # For each cluster(Base Cluster) visit the next clusters
        for entity in clusters:
            forward_index = index + 1
            # Search if next clusters are linked to this cluster
            for new_entity in clusters[forward_index:]:
                # Two clusters are linked in have at least one common mention
                # Search for a common mention
                for mention in entity:
                    # Are linked?
                    if mention in new_entity:
                        # The next cluster is coreferent to the original cluster
                        # Add the new mentions to first cluster
                        for new_mention in new_entity:
                            # A mention is new if doesn't exist in original cluster
                            if new_mention not in entity:
                                entity.append(new_mention)
                                # Add a register for debug proposes
                                registers[index] += self.sort_name + "|" + registers[forward_index]
                        # Reorder the mixed cluster
                        entity.sort(key=lambda x: self.graph.node[x]["span"])
                        # remove the merged cluster
                        del clusters[forward_index]
                        del registers[forward_index]
                        # this cluster was erased so next cluster has the same index
                        forward_index -= 1
                        # No further checks with the death cluster
                        break
                # Nest forward cluster
                forward_index += 1
            # Next cluster (Base cluster)
            index += 1

    def resolve(self, clusters, candidates_per_mention, register):
        """Compare each cluster, formed by a tuple of a list of mentions and a list of candidates.
        :param clusters: The list of pair entity candidatures that conform a text coreference proposal.
        :param candidates_per_mention: A dictionary of the candidates of each mention
        :param register: A register of de merges of each cluster
        """
        self.clusters = clusters
        #widgets = ['Passing sieve {0}: '.format(self.__class__), Fraction()]
        #progress_bar = ProgressBar(widgets=widgets, maxval=len(clusters) or 1, force_update=True).start()
        self.debug("Resolving %d clusters", len(clusters), indent=0)
        for cluster_index, entity in enumerate(clusters):
            # Get the first mention of the entity that is valid for the sieve
            self.debug("Resolving cluster: -%s-", entity, indent=1)
            mentions = self.valid_mention(entity)
            self.debug("Valid mentions: -%s-", mentions, indent=2)
            for mention_id in mentions:
                mention = self.graph.node[mention_id]
                speaker = self.get_speaker_id(mention)
                self.debug("Mention-%s- speaker %s utt %s quo %s",
                           mention["form"], speaker, mention["utterance"],
                           mention["quoted"], indent=2)
                self.debug("candidates: -%s-", candidates_per_mention[mention_id], indent=2)
                for candidate in candidates_per_mention[mention_id]:
                    if self.are_coreferent(entity, mention, self.graph.node[candidate]):
                        # If passed the sieve link candidate and stop search for that entity
                        self._link(entity, candidate)
                        # Break the search of candidates for this mention. Only one is elected
                        break
            #progress_bar.update(cluster_index + 1)
        #progress_bar.finish()
        self.merge(clusters, register)
        return clusters

    @staticmethod
    def _link(entity, candidate):
        """Link the candidate to the entity. Remove from candidates.
        :param candidate: The candidate that is going to be promoted into mention entity.
        :param entity: The entity that is going to receive the mention
        """
        entity.append(candidate)

    def entities_of_a_mention(self, mention):
        """ Return all the entities where a mention appears.
        :param mention: The mention whose entities are fetched.
        """
        return [
            entity
            for entity in self.clusters if mention["id"] in entity]

    def entity_property(self, entity, property_name):
        """ Get a combined property of the values of all mentions of the entity

        @param property_name: The name of the property to fetch.
        @param entity:  the entity of which property is fetched.
        """
        combined_property = set((
            self.graph.node[mention].get(property_name, None)
            for mention in entity))
        #if len(combined_property) > 1 and self.UNKNOWN in combined_property:
        #    combined_property.remove(self.UNKNOWN)
        if None in combined_property:
            combined_property.remove(None)
        return combined_property

    def candidate_property(self, candidate, property_name, clean=False):
        """ Get a combined property of the values of all mentions of the entities that candidate belongs.

        @param property_name: The name of the property to fetch.
        @param candidate:  the entity of which property is fetched.
        @param clean: Remove unknown form list if other attributes exist
        """
        combined_property = set((
            property_value
            for entity_involved in self.entities_of_a_mention(candidate)
            for property_value in self.entity_property(entity_involved, property_name)))

        if clean and len(combined_property) > 1 and self.UNKNOWN in combined_property:
            combined_property.remove(self.UNKNOWN)
        return combined_property

    def narrative_you(self, mention):
        """The mention is YOU person of the narrator(PER0) in an article.
        @param mention: The mention to check.
        """
        return mention["doc_type"] == "article" and mention["speaker"] == "PER0" and self.is_you(mention=mention)

    @staticmethod
    def is_first_person(mention):
        """ The mention is a first person singular pronoun.

        @param mention: The mention for check.
        """
        form = mention["form"].lower()
        return form in pronouns.first_person and form in pronouns.singular

    @staticmethod
    def is_we(mention):
        """ The Mention is a first person plural pronoun.

        @param mention: The mention for check.
        """
        form = mention["form"].lower()
        return form in pronouns.first_person and form in pronouns.plural

    @staticmethod
    def is_you(mention):
        """ The mention is a second person pronoun?

        @param mention: The mention for check.
        """
        return mention["form"].lower() in pronouns.second_person

    @staticmethod
    def is_pronoun(mention):
        """ The mentions is a pronoun mention?

        @param mention: The mention for check.
        """
        return mention["mention"] == "pronoun_mention"

    @staticmethod
    def is_undefined(mention):
        """ The mentions is am undefined mention?

        @param mention: The mention for check.
        """
        return mention["mention"] == "undefined_mention"

    @staticmethod
    def is_location(mention):
        """ The mentions is a location?

        @param mention: The mention for check.
        """
        return ner_tags.location(mention.get("ner", ner_tags.no_ner))

    def agree_attributes(self, entity, candidate):
        """ All attributes are compatible. Its mean the attributes of each are a subset one of the another.

        @param entity: Entity
        @param candidate: candidate
        @return: True or False
        """
        candidate_gender = self.candidate_property(candidate, "gender")
        entity_gender = self.entity_property(entity, "gender")
        if not (self.UNKNOWN.intersection(entity_gender) and self.UNKNOWN.intersection(candidate_gender)) or (
                candidate_gender.intersection(entity_gender)
                and
                entity_gender.intersection(candidate_gender)):
            return False
        
        candidate_number = self.candidate_property(candidate, "number")
        entity_number = self.entity_property(entity, "number")
        if not(self.UNKNOWN.intersection(entity_number) or self.UNKNOWN.intersection(candidate_number))or (
                candidate_number.intersection(entity_number)
                and
                entity_number.intersection(candidate_number)):
            return False
        
        candidate_animacy = self.candidate_property(candidate, "animacy")
        entity_animacy = self.entity_property(entity, "animacy")
        if not(self.UNKNOWN.intersection(entity_animacy) or self.UNKNOWN.intersection(candidate_animacy)) or (
                candidate_animacy.intersection(entity_animacy)
                and
                entity_animacy.intersection(candidate_animacy)):
            return False
        
        candidate_ner = self.candidate_property(candidate, "ner")
        entity_ner = self.entity_property(entity, "ner")
        if not(self.UNKNOWN.intersection(entity_ner) or self.UNKNOWN.intersection(candidate_ner)) or (
                candidate_ner.intersection(entity_ner)
                and
                entity_ner.intersection(candidate_ner)):
            return False

        return True

    def i_within_i(self, mention_a, mention_b):
        """ Check if the  mention and candidate aren't in a i-within-i construction.
        @param mention_a: a mention
        @param mention_b: another mention
        """
        if not self.graph_builder.same_sentence(mention_a, mention_b):
            return False
        #TODO Aren't appositive
        if self.tree_utils.is_appositive_construction_child(mention_a) and\
                self.tree_utils.is_appositive_construction_child(mention_b):
            return False
        #Aren't Relative pronouns
        if self.tree_utils.is_relative_pronoun(mention_b, mention_a) or \
                self.tree_utils.is_relative_pronoun(mention_a, mention_b):
            return False
        #One is included in the other
        if self.graph_builder.same_sentence(mention_a, mention_b):
            if self.graph_builder.is_inside(mention_a["span"], mention_b["span"]) or \
                    self.graph_builder.is_inside(mention_b["span"], mention_a["span"]):
                return True
        return False

    def same_speaker(self, mention_a, mention_b):
        """ Check if mention have the same speaker.
        @param mention_a: a mention
        @param mention_b: another mention
        @return:
        """
        speaker_a = mention_a["speaker"]
        speaker_b = mention_b["speaker"]
        if not(speaker_a and speaker_b):
            return False
        # Two speakers are the same
        if type(speaker_a) == str and type(speaker_b) == str and speaker_a == speaker_b:
            return True
        # Speaker A is B head word
        if self._check_speaker(speaker_a, mention_b):
            return True
        # Speaker B is A head word
        if self._check_speaker(speaker_b, mention_a):
            return True
        return False

    def _check_speaker(self, speaker, mention):
        """
        @param speaker:
        @param mention:
        @return:
        """
        if not (type(speaker) is str):
            speaker = speaker["form"]

        mention_head_form = self.graph_builder.get_head_word(mention)["form"]
        if mention_head_form == speaker:
            return True
        for speaker_token in speaker.split():
            if speaker_token == mention_head_form:
                return True
        return False

    @staticmethod
    def get_speaker_id(candidate):
        """ Get a string ID for a speaker. MAy be a  plain name or a node ID.

        @param candidate: The mention whose speaker is needed
        @return: A string, may be a node ID or a plain name.
        """
        try:
            speaker = candidate["speaker"]["id"]
        except TypeError:
            speaker = candidate["speaker"]
        return speaker

    def debug(self, message, *args, **kwargs):
        """  You a preformated debug for sieve logger.
        @param message: The message to show
        @param args: The message filling variables
        @param kwargs: Check for indent, for message indentation,
        """
        self.logger.debug("{0:5}{1}{2}".format(self.sort_name, '\t' * kwargs.get('indent', 3), message), *args)
