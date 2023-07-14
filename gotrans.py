#!/usr/local/bin/python

'''
#
# Purpose:
#
#	To translate an interpro2go or spkw2go file into a Translation Load input file
#
# Parameters:
#	-I = input file
#
# Output:
#
#	A tab-delimited file in this format:
#		field 1: Acc ID of MGI Object
#		field 2: GO Term
#		field 3: Translated Term
#		field 4: Created By
#
# History:
#
# lec	02/13/2003
#	- part of JSAM
#
'''

import sys
import os
import string
import re

#globals

inputFileName = os.environ['TRANSINPUTFILE']
createdBy = os.environ['CREATEDBY']

inputFile = ''		# file descriptor
outputFile = ''		# file descriptor
errorFile = ''		# file descriptor

delim = '\t'

def exit(status, message = None):
        '''
        # requires: status, the numeric exit status (integer)
        #           message (string)
        #
        # effects:
        # Print message to stderr and exits
        #
        # returns:
        #
        '''
 
        if message is not None:
                sys.stderr.write('\n' + str(message) + '\n')
 
        try:
                inputFile.close()
                outputFile.close()
                errorFile.close()
        except:
                pass

        sys.exit(status)
 
def init():
        '''
        # requires: 
        #
        # effects: 
        # 1. Processes command line options
        #
        # returns:
        #
        '''
 
        global inputFile, outputFile, errorFile
        global GO_re, TERM_re
 
        outputFileName = inputFileName + '.trans'
        errorFileName = inputFileName + '.error'

        try:
                inputFile = open(inputFileName, 'r')
        except:
                exit(1, 'Could not open file %s\n' % inputFileName)
                
        try:
                outputFile = open(outputFileName, 'w')
        except:
                exit(1, 'Could not open file %s\n' % outputFileName)
                
        try:
                errorFile = open(errorFileName, 'w')
        except:
                exit(1, 'Could not open file %s\n' % errorFileName)
                
        GO_re = re.compile(';.*(GO:[0-9]+)')

        if createdBy == 'interpro2go_load':
                TERM_re = re.compile(':(IPR[0-9]+) ')
        elif createdBy == 'spkw2go_load':
                TERM_re = re.compile('SP_KW:(.+) >')

def processFile():
        '''
        # requires:
        #
        # effects:
        #	Reads input file
        #	Writes output file
        #
        # returns:
        #	nothing
        #
        '''

        # For each line in the input file

        for line in inputFile.readlines():

                if line[0] == '!':
                        continue

                r = TERM_re.search(line)
                if r is not None:
                        term = r.group(1)
                else:
                        errorFile.write('Invalid Term: %s\n' % (line))
                        continue

                r = GO_re.search(line)
                if r is not None:
                        goID = r.group(1)
                else:
                        errorFile.write('Invalid GO ID: %s\n' % (line))
                        continue

                outputFile.write(goID + delim + delim + term + delim + createdBy + '\n')

#	end of "for line in inputFile.readlines():"

#
# Main
#

init()
processFile()
exit(0)

