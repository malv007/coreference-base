#!/usr/bin/python
# coding=utf-8
""" This module offers the possibility of process a entire corpus of kaf files with corefgraph

"""

__author__ = 'Josu Bermúdez <josu.bermudez@deusto.es>'
__created__ = '27/06/13'

try:
    from corefgraph import properties
except Exception as ex:
    import sys
    import os
    sys.path.append(os.getcwd())
    from corefgraph import properties

from file import generate_parser as generate_parser_for_file, process as process_file

import pycorpus

import argparse
import codecs
import logging
import datetime
import os
import re


# Logging
logger = logging.getLogger("corpusProcessor")

NAME_START = "result"
SPACE_CHAR = "_"
LINE_PATTERN = "{0:<20}\t{1}\t {2}\t {3}"


def generate_parser():
    """The parser used to provide configuration from experiment module to coreference module.

    Inherited all the properties from coreference module original parser and add tho more for
    handle the result store.

    :return: The parser
    """
    parser = argparse.ArgumentParser(parents=[generate_parser_for_file()], add_help=False)
    parser.add_argument('--result', dest='result', action='store', default="result",
                        help="")
    parser.add_argument('--metrics', dest='metrics', nargs="*", action='store',
                        default=["muc", "bcub", "ceafm", "ceafe", "blanc"],
                        help="The metric of the evaluation.")
    parser.add_argument('--speaker', dest='caption', action='store', default="",
                        help="The name of the configuration pack'")
    parser.add_argument('--output_eval_name', dest='caption', action='store', default="",
                        help="The name of the configuration pack")
    parser.add_argument('--speaker_extension', dest='speaker_extension', action='store', default=None,
                        help="")
    parser.add_argument('--treebank_extension', dest='treebank_extension', action='store', default=None,
                        help="")
    parser.add_argument('--evaluation_script', dest='evaluation_script', action='store', default="",
                        help="The script of evaluation'")
    parser.add_argument('--gold', dest='golden', action='store', default="",
                        help="The golden annotation.'")
    parser.add_argument('--external_tree', dest='use_external_tree_files', action='store_true')
    return parser


def file_processor(file_name, config):
    """ Extract from the base file the name of all the analysis needed for coreference analysis. Also if the
    result is in Conll format retrieve the part and de document name from filename.

    :param file_name: The file to bo resolved.
    :param config: The configuration for the coreference module.
    :return: NOTHING
    """
    logger.info("Start parsing %s", file_name)
    # Create the file names in base of original file name
    path, full_name = os.path.split(file_name)
    name, ext = os.path.splitext(full_name)
    base_name = os.path.join(path, name)

    store_file = base_name + "." + config.result
    kaf_filename = base_name + ext
    logger.debug("Reading KAF from: %s", kaf_filename)
    #files
    if config.treebank_extension:
        logger.info("Using TreeBank trees")
        tree_filename = base_name + config.treebank_extension
        try:
            trees = codecs.open(tree_filename, mode="r").read()
        except IOErrro as ex:
            trees = None
            logger.warning("Error in treebank file %s: %s", tree_filename, ex)
    else:
        logger.info("Using kaf trees")
        trees = None

    if config.speaker_extension:
        speaker_filename = base_name + config.speaker_extension
        try:
            speakers = codecs.open(speaker_filename, mode="r").read()
        except IOError as ex:
            logger.warning("Error in speaker file %s: %s", speaker_filename, ex)
            speakers = None
    else:
        speakers = None
        logger.debug("NO speaker file")

    # If is a Conll file add the document and part info
    if config.conll:
        #"--conll", "--document_id", document_id, "--part_id", part_id]
        config.__dict__["document_id"] = name.split("#")[0]
        config.__dict__["part_id"] = name.split("#")[1]

    # Open the files and pass the data to the module
    logger.info("Parsing stored in %s", store_file)
    with codecs.open(store_file, "w") as output_file:
        process_file(
            config=config,
            text=codecs.open(kaf_filename, mode="r").read(),
            parse_tree=trees,
            speakers_list=speakers,
            output=output_file)


def evaluate(general_config, experiment_config):
    """ Evaluates all the corpus and stores the result in files

    @param general_config: The configuration applicable to all corpus
    @param experiment_config: the configuration applicable to this file.
    """
    logger.info("Evaluating: %s", experiment_config.metrics)
    path, script = os.path.split(experiment_config.evaluation_script)
    for metric in experiment_config.metrics:
        command = [
            "sh",
            script,
            os.path.abspath(experiment_config.golden),
            os.path.abspath(experiment_config.golden),
            experiment_config.result,
            metric]
        logger.info("Metric: %s", metric)
        logger.debug("Command: %s", command)
        err, out = pycorpus.CorpusProcessor.launch_with_output(command, cwd=os.path.abspath(path))
        store_file = "{0}.{1}.{2}".format(NAME_START, experiment_config.caption, metric)
        logger.info("Evaluation stored in %s", store_file)
        with codecs.open(store_file, "w") as output_file:
            output_file.write(err)
            output_file.write(out)
    logger.info("Evaluation end.")


def report(general_config):
    """ Generate a email report of the experiment.
    @param general_config: The general config
    """
    report_text = generate_report(os.path.abspath("."))
    date = datetime.datetime.today().isoformat()
    pycorpus.CorpusProcessor.send_mail(general_config.mail_server, general_config.source_email,
                                       general_config.target_emails, report_text, "#Evaluacion " + date)


def generate_report(path):
    """ Find any result files in path and make a report with it.

    @param path:
    @return: a list of Strings with the report
    """

    file_list = [file_name for file_name in os.listdir(path) if file_name.startswith(NAME_START)]
    file_list.sort()
    results = []
    for file_name in file_list:
        inside = open(file_name).readlines()
        values = re.findall("\d+\.?\d*%", inside[-2])
        caption = file_name[7:].replace(SPACE_CHAR, " ")
        results.append(LINE_PATTERN.format(caption, values[0], values[1], values[2]))
    return "\n".join(results)


def main(filename=None):
    """ Run the experiments
    @param filename: The name of the parameter file"""
    experiment_instance = pycorpus.CorpusProcessor(
        generate_parser_function=generate_parser,
        process_file_function=file_processor,
        evaluation_script=evaluate,
        report_script=report)
    experiment_instance.run_corpus(filename)


if __name__ == "__main__":
    main()
