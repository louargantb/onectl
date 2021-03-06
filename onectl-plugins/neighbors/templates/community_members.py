#!/usr/bin/python -u

from includes import pluginClass
from includes import regexp
from includes import bash
import os
import sys
import re
import subprocess
import inspect

class PluginControl(pluginClass.Base):
	def setOptions(self):
		''' Add options after neighbors.conf.communities.COMM1.members plugin '''
		dic = []
		### OPTION: set
		opt = {}
		opt['name'] = '--set'
		opt['metavar'] = 'HOST'
		opt['action'] = 'store'
		opt['nargs'] = '+'
		opt['help'] = 'Configure host(s) for the specified community'
		dic.append(opt)

		### OPTION: add
		opt = {}
		opt['name'] = '--add'
		opt['metavar'] = 'HOST'
		opt['action'] = 'store'
		opt['nargs'] = '+'
		opt['help'] = 'Add host(s) to a community.'
		dic.append(opt)
		
		
		### OPTION: remove
		opt = {}
		opt['name'] = '--remove'
		opt['metavar'] = 'HOST'
		opt['action'] = 'store'
		opt['nargs'] = '+'
		opt['help'] = 'Remove host(s) for a community.'
		dic.append(opt)
	
		return dic
		
	def info(self):
		''' Information for the plugin'''
		title = self.PluginName+" configuration"
		msg = "Configure hosts for a community.\n"
		msg += "--set HOSNAME HOSTNAME ... \n"
		msg += "                  : List of hosts to be added to the community. Deletes the existing hosts in the community\n"
		msg += "                    eg: --set hostname1 hostname2 \n"
		msg += " \n"
		msg += "--add HOSTNAME    : Add a hist or list of hostss to the community.\n"
		msg += "--remove HOSTNAME : Remove host(s) from the community.\n"
		msg += "\n"
		msg += " NB: Hosts configured should be configured first in neighbors.names.\n"
		self.output.help(title, msg)
		
	def _get_community_name(self, plugin):
		''' get the community name from the plugin '''
		# neighbors.conf.communities.COMM1.members
		community = re.sub('.*communities.', '', re.sub('.members$', '', plugin))
		return community
	
	def get_active(self):
		''' get list of configured hosts in community '''
		try:
			community = self._get_community_name(self.PluginFqn)
			data = self.load_data()
			
			data_list = []
			if self.PluginFqn in data:
				data_list = data[self.PluginFqn].split()
			return data_list
		except:
			raise
			
	def get(self):
		try:
			''' Get configured neighbours '''
			
			# Get the configured neighbours
			members = self.get_active()
			self.output.title("Configured members:")
			self.output.info(' '.join(members))
			
		except:
			self.printError("Getting "+self.PluginName+" : ")
			return 1
		return 0
		
	def inputValidation(self, data):
		try:
			if not data:
				return data
			input_list = list(set(data))
			input_list = sorted(input_list)
			for hostname in input_list:
				if len(hostname) > 255:
					return False
					
				pattern=re.compile(regexp.HOSTNAME, re.VERBOSE | re.IGNORECASE)
				if  pattern.match(hostname) is None:
					raise ValueError('Invalid hostname %s' %hostname)
		except:
			self.printError("Validation failure for "+self.PluginName+" : ")
			return None
			
		return input_list
		
	def set(self, data):
		''' Add members to comunity. Deletes the previous ones'''
		try:
			# validate and transform input to list
			in_data = self.validate_input_data(data)
			
			# find the existing neighbours on the system
				
			self.output.info("Members added: %s "  %' '.join(in_data))
		except:
			self.printError("Set failure for "+self.PluginName+" : ")
			return 1
		return 0
	
	def check(self):
		''' Overwrite the check function.Needed for view diff.Check agains Onboot setup
		\n are removed from result from get function '''
		data_list = self.get_active()
		view_output = ' '.join(data_list)
		self._check(info_get=view_output)
	
	def add(self, data=''):
		''' Add new neighbour plugins to already existing config
			Takes the current config changes it and calls the set function
			Return 0 for OK and 1 for error
		'''
		try:
			input_data = self.validate_input_data(data)
			toadd = input_data
			plugin = self.PluginFqn
			
			curr_config = self.get_current_config(self.PluginFqn)
			#if the plugin is called for the first time no info saves load the current config
			is_db_config = True
			if not curr_config:
				is_db_config = False
				curr_config = self.get_active()
				
			for item in list(toadd):
				# if item is already in the current config remove it from list for adding
				if item in curr_config:
					toadd = list(filter(lambda curr: curr!= item, toadd))
					
			# if list for elements to be added is empty and the db is  exit
			#if db is emtry save the current config
			if not toadd and is_db_config:
				self.output.info("Value(s) " + ' '.join(input_data) + " for plugin "  +self.PluginName +  " already configured")
				return 0;
				
			# add the new elements to the current config
			curr_config.extend(toadd)
				
			# set new values
			res = self.set(curr_config)
			
			# if set was ok
			if res == 0:
				self.output.info("Added plugins "  + ' '.join(toadd))
		except:
			self.printError("Adding "+self.PluginName+" " + ' '.join(toadd)+": ")
			return 1
		return 0
		
	def remove(self, data=''):
		''' Delete neighbor plugins 
			Return 0 for OK and 1 for error
		'''
		plugin = self.PluginFqn
		
		try:
			# Check input and transform it to a list
			# remove duplicate values
			input_data = self.validate_input_data(data)
			todel = input_data
			
			#Get the configured servers
			current_config = self.get_current_config(self.PluginFqn)
			
			if not current_config:
				self.output.info("No " + self.PluginName + "(s) configured to be deleted")
				return 0
				
			bEntryRemoved=False
			for entry in todel:
				# if the entry is in current config remove it
				if entry in current_config:
					# iterate through the current config and remove the entry from command
					current_config = list(filter(lambda curr: curr!= entry, current_config))
					bEntryRemoved=True
						
			# if no entries were removed show a message and exit
			if not bEntryRemoved:
				self.output.info("Value(s) " + ' '.join(input_data)  + " for plugin " + self.PluginName + " is(are) not configured.")
				return 0
			
			#for neighbour in data:
			#	self.removePlugin("neighbour.conf."+neighbour+".ip")
			#self.output.disable()
			res = self.set(current_config)
					
			if res == 0:
				self.output.info("Deleted plugins "  + ' '.join(todel))
		except:
			self.printError("Removing "+self.PluginName+" " + ' '.join(todel)+": ")
			return 1
		return 0

	def init(self):
		''' Ger get currently configured hosts in /etc/hosts and create plugins'''
		#hostname = self._get_hostname(self.PluginFqn)
		# Set IP active
		# Get the configured neighbors
		try:
			hosts_file='/etc/hosts'
			file_config = open(hosts_file, 'r')
			file_lines = file_config.readlines()
			file_config.close()
		
			output = {}
			bHostsMod = False
			for line in file_lines:
				#if re.search(r'\b%s\b' % (re.escape(hostname)), line):
				#if re.search(hostname, line):
				result = line.split()
				if not len(result) > 1:
					continue
				ip = result[0]
				host = result[1]
				if host == 'localhost':
					continue
				if ip == '127.0.0.1' or ip == '::1':
					continue
				output[host] = ip
				#output.append(host:ip)
			neighbours = output.keys()
			self.set(neighbours)
			for neighbour in output:
				ip_plugin = "neighbors.conf." + neighbour + ".ip"
				#self.createPlugin("neighbors/neighbour_ip.py", ip_plugin)
				#self.createPlugin("neighbors/neighbour_ssh.py", "neighbors.conf." + neighbour + ".ssh")
				self.executePlugin(ip_plugin, "set", output[neighbour])
			return output
		except:
			raise
	
	def browse(self, eth):
		try:
			if not eth:
				eth = "all"
			if eth != "all":
				res, err = bash.run('ifconfig '+eth)
				if err:
					self.output.error(eth + " not present on this system !")
					return -1
				
			neigbors = {}
			res, err = bash.run('timeout 5 avahi-browse -krptaf')
			lines = res.replace('\\032', ' ').replace('\\091', '[').replace('\\058', ':').replace('\\093', ']').split('\n')
			lines = filter(None, lines)
			if len(lines) == 0:
				self.output.warning("No host found on the network.")
				self.output.warning("You should check that the hostname is correctly set")
				self.output.warning("and the service avahi-daemon is running.")
				
			for line in lines:
				if line:
					#=;eth0;IPv4;linux-4 [52:54:00:10:8e:76];_workstation._tcp;local;linux-4.local;10.165.110.102;9;
					#=;eth0;IPv4;KVM-HSV-HS22C;_ssh._tcp;local;KVM-HSV-HS22C.local;192.168.122.1;22;
					#=;eth0;IPv4;Virtualization Host fr-cae-kvm33;_libvirt._tcp;local;fr-cae-kvm33.local;10.165.110.33;65535;"qemu"
					info = line.split(';')
					name = info[3]
					iface = info[1]
					service = info[4]
					ip = ''
					mac = ''
					if len(info) > 6:
						ip = info[7]
					if service == "_workstation._tcp":
						name = re.sub(r' \[.*', '', info[3])
						mac = re.sub(r'.* \[', '', info[3]).replace(']', '')
						service = ""
					elif service == "_libvirt._tcp":
						name = re.sub(r'Virtualization Host ', '', info[3])
						service = "Virtualization"
					elif service == "_ssh._tcp":
						service = "SSH"
					
					if eth == "all" or iface == eth:
						if not neigbors.has_key(iface):
							neigbors[iface] = {}
						if not neigbors[iface].has_key(name):
							neigbor = {}
							neigbor['ip'] = ip
							neigbors[iface][name] = neigbor
							neigbors[iface][name]['services'] = []
						if mac != "":
							neigbors[iface][name]['mac'] = mac
						if ip != "":
							neigbors[iface][name]['ip'] = ip
						if service and service not in neigbors[iface][name]['services']:
							neigbors[iface][name]['services'].append(service)
					
					
			ifaces = sorted(neigbors.keys())
			for iface in ifaces:
				self.output.title("Hosts on interface %s:" %iface)
				for host in sorted(neigbors[iface].keys()):
					ip = neigbors[iface][host]['ip']
					host_info = "%s @ %s" % (host, ip)
					if neigbors[iface][host].has_key('mac'):
						mac = neigbors[iface][host]['mac']
						host_info += " (%s)" % mac
					if len(neigbors[iface][host]['services']) > 0:
						host_info += " - %s" % neigbors[iface][host]['services']
					self.output.info(host_info)
		except:
			self.printError("Browsing LAN: ")
			return 1
		return 0


