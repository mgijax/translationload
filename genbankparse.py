#!/usr/local/bin/python

'''
#
# Purpose:
#
#       To parse a GenBank comparison file into an input file for Translation Load
#
# Assumes:
#
# Side Effects:
#
#	None
#
# Input(s):
#
# Output:
#
#       A tab-delimited file in this format:
#               field 1: Acc ID of MGI Object
#               field 2: MGI Object
#               field 3: Translated Term
#               field 4: Created By
#
#	Diagnostics file of all input parameters and SQL commands
#	Error file
#
# History:
#
# lec	01/26/2004
# lec	01/26/2004
#	- part of JSAM
#
'''

import sys
import os
import string
import db
import mgi_utils

#globals

user = os.environ['MGD_DBUSER']
passwordFileName = os.environ['MGD_DBPASSWORDFILE']
createdBy = os.environ['CREATEDBY']
inputFileName = os.environ['TRANSINPUTFILE']
parseType = os.environ['TRANSPARSETYPE']

inputFile = ''		# file descriptor
outputFile = ''		# file descriptor
diagFile = ''		# file descriptor
errorFile = ''		# file descriptor

diagFileName = ''	# file name
errorFileName = ''	# file name

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
		diagFile.write('\n\nEnd Date/Time: %s\n' % (mgi_utils.date()))
		errorFile.write('\n\nEnd Date/Time: %s\n' % (mgi_utils.date()))
		diagFile.close()
		errorFile.close()
	except:
		pass

	db.useOneConnection()
	sys.exit(status)
 
def init():
	'''
	# requires: 
	#
	# effects: 
	# 1. Processes command line options
	# 2. Initializes local DBMS parameters
	# 3. Initializes global file descriptors/file names
	# 4. Initializes global keys
	#
	# returns:
	#
	'''
 
	global inputFile, outputFile, diagFile, errorFile, errorFileName, diagFileName
 
	db.useOneConnection(1)
        db.set_sqlUser(user)
        db.set_sqlPasswordFromFile(passwordFileName)
 
	diagFileName = inputFileName + '.diagnostics'
	errorFileName = inputFileName + '.error'
 	outputFileName = inputFileName + '.trans'

	try:
		inputFile = open(inputFileName, 'r')
	except:
		exit(1, 'Could not open file %s\n' % inputFileName)
		
	try:
		diagFile = open(diagFileName, 'w')
	except:
		exit(1, 'Could not open file %s\n' % diagFileName)
		
	try:
		errorFile = open(errorFileName, 'w')
	except:
		exit(1, 'Could not open file %s\n' % errorFileName)
		
	try:
		outputFile = open(outputFileName, 'w')
	except:
		exit(1, 'Could not open file %s\n' % outputFileName)
		
	# Log all SQL
	db.set_sqlLogFunction(db.sqlLogAll)

	# Set Log File Descriptor
	db.set_sqlLogFD(diagFile)

	diagFile.write('Start Date/Time: %s\n' % (mgi_utils.date()))
        diagFile.write('Server: %s\n' % (db.get_sqlServer()))
        diagFile.write('Database: %s\n' % (db.get_sqlDatabase()))
	diagFile.write('Input File: %s\n' % (inputFileName))
	diagFile.write('Output File: %s\n' % (outputFileName))

	errorFile.write('Start Date/Time: %s\n\n' % (mgi_utils.date()))

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

		tokens = string.split(line[:-1], delim)

		try:
			if parseType == 'Library':
			    badName = tokens[0]
			    goodName = tokens[2]
			else:
			    badName = tokens[1]
			    goodName = tokens[2]

		except:
			errorFile.write('Invalid line: %s\n' % (line))
			continue

		if parseType == 'Tissues':
		    results = db.sql('select _Tissue_key from PRB_Tissue where tissue = "%s"' % (goodName), 'auto')
		elif parseType == 'Cell':
		    results = db.sql('select term from VOC_Term where term = "%s"' % (goodName), 'auto')
		elif parseType == 'Library':
		    results = db.sql('select _Source_key from PRB_Source where name = "%s"' % (goodName), 'auto')
		elif parseType == 'Strains':
		    results = db.sql('select a.accID from PRB_Strain_Acc_View a, PRB_Strain s ' + \
			'where s.strain = "%s" ' % (goodName) + \
			'and s._Strain_key *= a._Object_key ' + \
			'and a._LogicalDB_key = 1 ' + \
			'and a.prefixPart = "MGI:" ' + \
			'and a.preferred = 1', 'auto')

		if len(results) > 0 and badName != goodName:
			if parseType == 'strain':
			  outputFile.write(mgi_utils.prvalue(results[0]['accID']) + delim + goodName + delim + badName + delim + createdBy + '\n')
			else:
			  outputFile.write(delim + goodName + delim + badName + delim + createdBy + '\n')
		elif len(results) == 0:
			errorFile.write('Invalid good name: %s\n' % (goodName))

#	end of "for line in inputFile.readlines():"
#
# Main
#

init()
processFile()
exit(0)

