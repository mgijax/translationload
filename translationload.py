#!/usr/local/bin/python

'''
#
# Purpose:
#
#	To load new/replace existing translation records into Translation structures:
#
#	MGI_TranslationType
#	MGI_Translation
#
# Assumes:
#
# Side Effects:
#
#	None
#
# Input(s):
#
#	A tab-delimited file in the format:
#		field 1: Acc ID of Good Name
#		field 2: Good Name
#		field 3: Bad Name
#		field 4: Created By
#
# Parameters:
#
#	processing modes:
#		fullest - delete the exisiting Translation Type and the existing Translations (if they exist)
#			load new Translations
#
#		full - delete the existing Translations (but not the Translation Type) (if they exist)
#			load new Translations
#
#		preview - perform all record verifications but do not load the data or
#		          make any changes to the database.  
#			  used for testing or to preview the load.
#
# Output:
#
#       2 BCP files:
#
#       MGI_TranslationType.bcp         Translation Type record
#	MGI_Translation.bcp		Translation records
#
#	Diagnostics file of all input parameters and SQL commands
#	Error file
#
# Processing:
#
#	1. Verify Mode.
#		if mode = fullest: delete MGI_TranslationType records
#		if mode = full: delete MGI_Translation records
#		if mode = preview:  set "DEBUG" to True
#
#	2.  Verify the Translation Type.
#
#	    If the Translation Type record exists and mode = fullest then
#		delete Translation Type record (and hence, all translations)
#	  	create a new Translation Type record
#
#	    If the Translation Type record exists and mode = full then
#		delete translation records for that translation type
#
#	    else if the Translation Type record exists and mode = preview then
#		do nothing here
#
#	For each line in the input file:
#
#	1.  Verify the Acc ID of the object (good name ) is valid.  
#	    The MGI Type of the Acc ID must be the same as the MGI Type of the Translation Type.
#	    Duplciate Acc IDs are allowed (a good name can have more than one bad name).
#	    If the verification fails, report the error and skip the record.
#
#	2.  Create MGI_Translation record for the MGI object.
#
# History:
#
# lec	03/21/2006
# lec	03/21/2006
#	- to support MGI 3.44/SNP data load; added "fullest" mode
#
# lec	02/13/2003
#	- part of JSAM
#
'''

import sys
import os
import string
import db
import mgi_utils
import loadlib

#globals

user = os.environ['MGD_DBUSER']
passwordFileName = os.environ['MGD_DBPASSWORDFILE']
mode = os.environ['TRANSMODE']
inputFileName = os.environ['TRANSINPUTFILE']
outputFileDir = os.environ['TRANSOUTPUTDIR']
transTypeName = os.environ['TRANSTYPENAME']
transMGIType = os.environ['TRANSMGITYPE']
transCompression = os.environ['TRANSCOMPRESSION']
vocabName = os.environ['VOCABNAME']

DEBUG = 0		# set DEBUG to false unless preview mode is selected

inputFile = ''		# file descriptor
diagFile = ''		# file descriptor
errorFile = ''		# file descriptor

transTypeFile = ''	# file descriptor
transFile = ''		# file descriptor

diagFileName = ''	# file name
errorFileName = ''	# file name

transTypeFileName = ''	# file name
transFileName = ''	# file name

bcpdelim = '\t'

transTypeKey = 0	# primary key of translation type record
mgiTypeKey = 0		# primary key of translation type mgi type
vocabKey = 0		# primary key of translation's vocabulary
newTransType = 0	# flags whether to create new Trans Type record

loaddate = loadlib.loaddate

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
		diagFile.write('\n\nEnd Date/Time: %s\n' % (mgi_utils.date()))
		errorFile.write('\n\nEnd Date/Time: %s\n' % (mgi_utils.date()))
		diagFile.close()
		errorFile.close()
		transTypeFile.close()
		transFile.close()
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
 
	global inputFile, diagFile, errorFile, errorFileName, diagFileName
	global transTypeFile, transFile
	global transTypeFileName, transFileName
 
	db.useOneConnection(1)
        db.set_sqlUser(user)
        db.set_sqlPasswordFromFile(passwordFileName)

	# the default output file names are bases on 'inputFileName'
	head, fileName = os.path.split(inputFileName)
	# rename 'head'
	head = outputFileDir 
	fdate = mgi_utils.date('%m%d%Y')	# current date

	diagFileName = head + '/' + fileName + '.' + fdate + '.diagnostics'
	print diagFileName
        errorFileName = head + '/' + fileName + '.' + fdate + '.error'
	print errorFileName
        transTypeFileName = head + '/' + fileName + '.' + fdate + '.MGI_TranslationType.bcp'
	print transTypeFileName
        transFileName = head + '/' + fileName + '.' + fdate + '.MGI_Translation.bcp'
	print transFileName

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
		transTypeFile = open(transTypeFileName, 'w')
	except:
		exit(1, 'Could not open file %s\n' % transTypeFileName)
		
	try:
		transFile = open(transFileName, 'w')
	except:
		exit(1, 'Could not open file %s\n' % transFileName)
		
	# Log all SQL
	db.set_sqlLogFunction(db.sqlLogAll)

	# Set Log File Descriptor
	db.set_sqlLogFD(diagFile)

	diagFile.write('Start Date/Time: %s\n' % (mgi_utils.date()))
        diagFile.write('Server: %s\n' % (db.get_sqlServer()))
        diagFile.write('Database: %s\n' % (db.get_sqlDatabase()))
	diagFile.write('Input File: %s\n' % (inputFileName))

	errorFile.write('Start Date/Time: %s\n\n' % (mgi_utils.date()))

def verifyMode():
	'''
	# requires:
	#
	# effects:
	#	Verifies the processing mode is valid.  If it is not valid,
	#	the program is aborted.
	#	Sets globals based on processing mode.
	#	Deletes data based on processing mode.
	#
	# returns:
	#	nothing
	#
	'''

	global DEBUG

	if mode == 'preview':
		DEBUG = 1
	elif mode not in ['fullest', 'full']:
		exit(1, 'Invalid Processing Mode:  %s\n' % (mode))

def processTranslationType():
	'''
	# requires:
	#
	# effects:
	#	checks if a TranslationType record exists
	#	if yes and mode == 'fullest', delete it and add a new record
	#	if yes and mode == 'full', delete existing translations of that translation type
	#	if no, creates a new one
	#	sets global transTypeKey, mgiTypeKey, vocabKey
	#
	# returns:
	#
	'''

	global transTypeKey, mgiTypeKey, vocabKey, newTransType

	newTransType = 0

	results = db.sql('select _TranslationType_key, _MGIType_key from MGI_TranslationType ' + \
		'where translationType = "%s" ' % (transTypeName), 'auto')

	# if Translation Type exists....

	if len(results) > 0:

		transTypeKey = results[0]['_TranslationType_key']
		mgiTypeKey = results[0]['_MGIType_key']

	        # delete any existing translation type record
	        if mode == 'fullest':
		    db.sql('delete from MGI_TranslationType where _TranslationType_key = %s' % (transTypeKey), None, execute = not DEBUG)
		    newTransType = 1

	        # delete any existing translation records (but leave translation type alone)
		elif mode == 'full':
		    db.sql('delete from MGI_Translation where _TranslationType_key = %s' % (transTypeKey), None, execute = not DEBUG)

	# else, create a new Translation Type

	else:
	    newTransType = 1

	if newTransType:

		results = db.sql('select maxKey = max(_TranslationType_key) + 1 from MGI_TranslationType', 'auto')
		transTypeKey = results[0]['maxKey']
		if transTypeKey is None:
			transTypeKey = 1000

		results = db.sql('select _MGIType_key from ACC_MGIType where name = "%s"' % (transMGIType), 'auto')
		mgiTypeKey = results[0]['_MGIType_key']

		newTransType = 1

	results = db.sql('select _Vocab_key from VOC_Vocab where name = "%s"' % (vocabName), 'auto')
	if len(results) > 0:
	    vocabKey = results[0]['_Vocab_key']
        else:
	    vocabKey = 0

def processFile():
	'''
	# requires:
	#
	# effects:
	#	Reads input file
	#	Verifies and Processes each line in the input file
	#
	# returns:
	#	nothing
	#
	'''

	results = db.sql('select maxKey = max(_Translation_key) + 1 from MGI_Translation', 'auto')
	transKey = results[0]['maxKey']
	if transKey is None:
		transKey = 1000

	lineNum = 0

	# sequence number of bad name in translation list
	seq = 1

	# For each line in the input file

	for line in inputFile.readlines():

		error = 0
		lineNum = lineNum + 1

		# Split the line into tokens
		tokens = string.split(line[:-1], '\t')

		try:
			objectID = tokens[0]
			objectDescription = tokens[1]
			term = tokens[2]
			userID = tokens[3]
		except:
			exit(1, 'Invalid Line (%d): %s\n' % (lineNum, line))
			continue

		if vocabKey > 0:
		    objectKey = loadlib.verifyTerm(objectID, vocabKey, objectDescription, lineNum, errorFile)
		else:
		    objectKey = loadlib.verifyObject(objectID, mgiTypeKey, objectDescription, lineNum, errorFile)

		userKey = loadlib.verifyUser(userID, lineNum, errorFile)

		if objectKey == 0 or userKey == 0:
			# set error flag to true
			error = 1

		# if errors, continue to next record
		if error:
			continue

		# if no errors, process

		# add term to translation file
		bcpWrite(transFile, [transKey, transTypeKey, objectKey, term, seq, userKey, userKey, loaddate, loaddate])
		transKey = transKey + 1
		seq = seq + 1

#	end of "for line in inputFile.readlines():"

	if newTransType:
		bcpWrite(transTypeFile, [transTypeKey, mgiTypeKey, vocabKey, transTypeName, transCompression, 0, userKey, userKey, loaddate, loaddate])

def bcpWrite(fp, values):
	'''
	#
	# requires:
	#	fp; file pointer of bcp file
	#	values; list of values
	#
	# effects:
	#	converts each value item to a string and writes out the values
	#	to the bcpFile using the appropriate delimiter
	#
	# returns:
	#	nothing
	#
	'''

	# convert all members of values to strings
	strvalues = []
	for v in values:
		strvalues.append(str(v))

	fp.write('%s\n' % (string.join(strvalues, bcpdelim)))

def bcpFiles():
	'''
	# requires:
	#
	# effects:
	#	BCPs the data into the database
	#
	# returns:
	#	nothing
	#
	'''

	transTypeFile.close()
	transFile.close()

	cmd1 = 'cat %s | bcp %s..%s in %s -c -t\"%s" -S%s -U%s' \
		% (passwordFileName, db.get_sqlDatabase(), \
	   	'MGI_TranslationType', transTypeFileName, bcpdelim, db.get_sqlServer(), db.get_sqlUser())

	cmd2 = 'cat %s | bcp %s..%s in %s -c -t\"%s" -S%s -U%s' \
		% (passwordFileName, db.get_sqlDatabase(), \
	   	'MGI_Translation', transFileName, bcpdelim, db.get_sqlServer(), db.get_sqlUser())

	diagFile.write('%s\n' % cmd1)
	diagFile.write('%s\n' % cmd2)

	if DEBUG:
		return

	os.system(cmd1)
	os.system(cmd2)

#
# Main
#

init()
verifyMode()
processTranslationType()
processFile()
bcpFiles()
exit(0)

