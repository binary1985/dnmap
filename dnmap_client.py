#! /usr/bin/env python
import sys,time, getopt, shlex, os, random
from subprocess import Popen
from subprocess import PIPE

# Global variables
server_ip = False
server_port = 46001 
vernum = '0.1fork'
# Your name alias defaults to anonymous
alias='Fork'
debug=False
output_file = 'dnmap_client_output.txt'
# End global variables

class NmapClient(LineReceiver):
	def connectionMade(self):
		global client_id
		global alias
		global debug
		print 'Client connected succesfully...'
		print 'Waiting for more commands....'
		if debug:
			print ' -- Your client ID is: {0} , and your alias is: {1}'.format(str(client_id), str(alias))

		euid = os.geteuid()

		# Do not send the euid, just tell if we are root or not.
		if euid==0:
			# True
			iamroot = 1
		else:
			# False
			iamroot = 0

		# 'Client ID' text must be sent to receive another command
		line = 'Starts the Client ID:{0}:Alias:{1}:Version:{2}:ImRoot:{3}'.format(str(client_id),str(alias),vernum,iamroot)
		if debug:
			print ' -- Line sent: {0}'.format(line)
		self.sendLine(line)

		#line = 'Send more commands to Client ID:{0}:Alias:{1}:\0'.format(str(client_id),str(alias))
		line = 'Send more commands'
		if debug:
			print ' -- Line sent: {0}'.format(line)
		self.sendLine(line)

	

	def dataReceived(self, line):
		global debug
		global client_id
		global alias
                global output_file

		# If a wait is received. just wait.
		if 'Wait' in line:
			sleeptime = int(line.split(':')[1])
			time.sleep(sleeptime)

			# Ask for more
			#line = 'Send more commands to Client ID:{0}:Alias:{1}:'.format(str(client_id),str(alias))
			line = 'Send more commands'
			if debug:
				print ' -- Line sent: {0}'.format(line)
			self.sendLine(line)
		else:
			# dataReceived does not wait for end of lines or CR nor LF
			if debug:
				print "\tCommand Received: {0}".format(line.strip('\n').strip('\r'))
		
			# A little bit of protection from the server
			if check_clean(line):
				# Store the nmap output file so we can send it to the server later
				try:
					nmap_output_file = line.split('-oA ')[1].split(' ')[0].strip(' ')
				except IndexError:
					random_file_name = str(random.randrange(0, 100000000, 1))
					print '+ No -oA given. We add it anyway so not to lose the results. Added -oA '+random_file_name
					line = line + '-oA '+random_file_name
					nmap_output_file = line.split('-oA ')[1].split(' ')[0].strip(' ')


				try:
					nmap_returncode = -1

					# Check for rate commands
					# Verfiy that the server is NOT trying to force us to be faster. NMAP PARAMETER DEPENDACE
					if 'min-rate' in line:
						temp_vect = shlex.split(line)
						word_index = temp_vect.index('--min-rate')
						# Just delete the --min-rate parameter with its value
						nmap_command = temp_vect[0:word_index] + temp_vect[word_index + 1:]
					else:
						nmap_command = shlex.split(line)
                                        
					# Recreate the final command to show it
					nmap_command_string = ''
					for i in nmap_command:
						nmap_command_string = nmap_command_string + i + ' '
					print "\tCommand Executed: {0}".format(nmap_command_string)

					nmap_process = Popen(nmap_command,executable='nmap',stdout=PIPE)
					raw_nmap_output = nmap_process.communicate()[0]

                                        #guadalajaraCON
                                        with open(str(output_file),'w+') as fp_client_output:
                                                fp_client_output.write(raw_nmap_output)
                                        fp_client_output.closed

					nmap_returncode = nmap_process.returncode
		

				except Exception:
					print 'Problem in dataReceived function'


				if nmap_returncode >= 0:
					# Nmap ended ok

					# Tell the server that we are sending the nmap output
					print '\tSending output to the server...'
					#line = 'Nmap Output File:{0}:{1}:{2}:'.format(nmap_output_file.strip('\n').strip('\r'),str(client_id),str(alias))
					line = 'Nmap Output File:{0}:'.format(nmap_output_file.strip('\n').strip('\r'))
					if debug:
						print ' -- Line sent: {0}'.format(line)
					self.sendLine(line)
					self.sendLine(raw_nmap_output)
					#line = 'Nmap Output Finished:{0}:{1}:{2}:'.format(nmap_output_file.strip('\n').strip('\r'),str(client_id),str(alias))
					line = 'Nmap Output Finished:{0}:'.format(nmap_output_file.strip('\n').strip('\r'))
					if debug:
						print ' -- Line sent: {0}'.format(line)
					self.sendLine(line)

					# Move nmap output files to its directory
					os.system('mv *.nmap nmap_output > /dev/null 2>&1')
					os.system('mv *.gnmap nmap_output > /dev/null 2>&1')
					os.system('mv *.xml nmap_output > /dev/null 2>&1')

					# Ask for another command.
					# 'Client ID' text must be sent to receive another command
					print 'Waiting for more commands....'
					#line = 'Send more commands to Client ID:{0}:Alias:{1}:'.format(str(client_id),str(alias))
					line = 'Send more commands'
					if debug:
						print ' -- Line sent: {0}'.format(line)
					self.sendLine(line)
			else:
				# Something strange was sent to us...
				print
				print 'WARNING! Ignoring some strange command was sent to us: {0}'.format(line)
				line = 'Send more commands'
				if debug:
					print ' -- Line sent: {0}'.format(line)
				self.sendLine(line)




class NmapClientFactory(ReconnectingClientFactory):
	try:
		protocol = NmapClient

		def startedConnecting(self, connector):
			print 'Starting connection...'

		def clientConnectionFailed(self, connector, reason):
			print 'Connection failed:', reason.getErrorMessage()
			# Try to reconnect
			print 'Trying to reconnect. Please wait...'
			ReconnectingClientFactory.clientConnectionLost(self, connector, reason)

		def clientConnectionLost(self, connector, reason):
			print 'Connection lost. Reason: {0}'.format(reason.getErrorMessage())
			# Try to reconnect
			print 'Trying to reconnect in 10 secs. Please wait...'
			ReconnectingClientFactory.clientConnectionLost(self, connector, reason)
	except Exception as inst:
		print 'Problem in NmapClientFactory'
		print type(inst)
		print inst.args
		print inst




def process_commands():
	global server_ip
	global server_port
	global client_id
	global factory
	try:

		print 'Client Started...'

		# Generate the client unique ID
		client_id = str(random.randrange(0, 100000000, 1))

		# Create the output directory
		print 'Nmap output files stored in \'nmap_output\' directory...'
		os.system('mkdir nmap_output > /dev/null 2>&1')

		factory = NmapClientFactory()
		# Do not wait more that 10 seconds between reconnections
		factory.maxDelay = 10

		reactor.connectSSL(str(server_ip), int(server_port), factory, ssl.ClientContextFactory())
		#reactor.addSystemEventTrigger('before','shutdown',myCleanUpFunction)
		reactor.run()
	except Exception as inst:
		print 'Problem in process_commands function'
		print type(inst)
		print inst.args
		print inst



def main():
	global server_ip
	global server_port
	global alias
	global debug
	global maxrate
        global output_file
	try:
		opts, args = getopt.getopt(sys.argv[1:], "a:dm:p:s:o:", ["server-ip=","server-port","max-rate","alias=","debug", "output="])

	except getopt.GetoptError: usage()

	for opt, arg in opts:
	    if opt in ("-s", "--server-ip"): server_ip=str(arg)
	    if opt in ("-p", "--server-port"): server_port=arg
	    if opt in ("-a", "--alias"): alias=str(arg).strip('\n').strip('\r').strip(' ')
            if opt in ("-o", "--output"): output_file=str(arg).strip('\n').strip('\r').strip(' ')
	    if opt in ("-d", "--debug"): debug=True
	    if opt in ("-m", "--max-rate"): maxrate=str(arg)

	try:

		if server_ip and server_port:

			version()

			# Start connecting
			process_commands()

		else:
			usage()


	except KeyboardInterrupt:
		# CTRL-C pretty handling.
		print "Keyboard Interruption!. Exiting."
		sys.exit(1)


if __name__ == '__main__':
    main()
