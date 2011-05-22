from ircbot import SingleServerIRCBot
from irclib import nm_to_n, nm_to_h, irc_lower, ip_numstr_to_quad, ip_quad_to_numstr
from datetime import datetime

class TestBot(SingleServerIRCBot):
	ruleversions = ["rules/rules.txt"]
	powerusers = []
	points = dict()

	def __init__(self, channel, nickname, server, port=6667):
		SingleServerIRCBot.__init__(self, [(server, port)], nickname, nickname)
		self.channel = channel
		f = open("rules/versions.txt")
		for line in f:
			self.ruleversions.append(line.strip("\n"))
		f.close()
		f = open("users.txt")
		for line in f:
			self.powerusers.append(line.strip("\n"))
		f.close()
		f = open("points.txt")
		for line in f:
			user, points = line.strip("\n").split(" - ")
			self.points[user] = int(points)
		f.close()

	def on_nicknameinuse(self, c, e):
		c.nick(c.get_nickname() + "_")

	def on_welcome(self, c, e):
		# I've commented out the preceding line as it should be used to identify with the server and had a password in it.
		# c.privmsg("NickServ", "IDENTIFY")
		c.join(self.channel)

	def on_privmsg(self, c, e):
		self.do_command(e, e.arguments()[0])

	#responds to public commands if addressed directly
	def on_pubmsg(self, c, e):
		a = e.arguments()[0].split(",", 1)
		print datetime.now().strftime("%d/%m/%y %H:%M:%S") + " <" + nm_to_n(e.source()) + "> " + e.arguments()[0]
		if len(a) > 1 and irc_lower(a[0]) == irc_lower(self.connection.get_nickname()):
			self.do_command(e, a[1].strip())
		return

	def on_dccmsg(self, c, e):
		c.privmsg("You said: " + e.arguments()[0])

	def on_dccchat(self, c, e):
		if len(e.arguments()) != 2:
			return
		args = e.arguments()[1].split()
		if len(args) == 4:
			try:
				address = ip_numstr_to_quad(args[2])
				port = int(args[3])
			except ValueError:
				return
			self.dcc_connect(address, port)
			
	def getDB(self):
		f = open(self.ruleversions[len(self.ruleversions)-1].strip("\n"))
		db = dict()
		for line in f:
			item = line[line.find(" ") + 1:]
			key = int(line[:line.find(" ") - 1])
			db[key] = item.strip("\n")
		f.close()
		return db
		
	#This function attempted to bypass IRC protocol's 433 char limit per line
	def say(self, who, text):
		c = self.connection
		charlimit = 433
		loops = len(text)/charlimit
		print datetime.now().strftime("%d/%m/%y %H:%M:%S") + " " + text
		for x in range(loops):
			c.privmsg(who, text[x*charlimit:(x+1)*charlimit])
		c.privmsg(who, text[loops*charlimit:len(text)])
		
	def updateversions(self):
		f = open("rules/versions.txt", "w")
		for version in self.ruleversions[1:]:
			f.write(version + "\n")
		f.close()
		
	def contains(self, array, item):
		try:
			array.index(item)
		except:
			return False
		else:
			return True

	def do_command(self, e, cmd):
		nick = nm_to_n(e.source())
		args = cmd.split(" ")

		if (cmd == "disconnect") & (self.contains(self.powerusers, nick)):
			self.disconnect()
		elif (cmd == "die") & (self.contains(self.powerusers, nick)):
			self.updateversions()
			self.die()
		elif (args[0] == "user") & (self.contains(self.powerusers, nick)):
			if args[1] == "add":
				self.powerusers.append(args[2])
			elif args[1] == "del":
				pass
			f = open("users.txt", "w")
			for user in self.powerusers:
				f.write(user + "\n")
			f.close()
			self.say(self.channel, nm_to_n(args[2]) + " was added successfully.")
		elif args[0] == "rule":
			rules = self.getDB()
			try:
				if len(args) == 2:
					self.say(self.channel, args[1] + ". " + rules[int(args[1])])
				else:
					self.say(self.channel, "format: NomicBot, rule <number>")
			except:
				self.say(self.channel, "That rule does not exist.")
		elif args[0] == "rules":
			rules = self.getDB()
			if len(args) == 1:
				for rule in sorted(rules.items()):
					self.say(nick, str(rule[0]) + ". " + rule[1])
			else:
				for arg in cmd[5:].split(","):
					arg = arg.strip()
					if (arg.find("-") == -1) & arg.isdigit():
						try:
							self.say(nick, arg + ". " + rules[int(arg)])
						except KeyError:
							self.say(nick, "Rule " + arg + " does not exist.")
					else:
						x = arg.split("-")
						try:
							for y in range(int(x[0]), int(x[1])+1):
								self.say(nick, str(y) + ". " + rules[y])
						except ValueError:
							self.say(nick, 'Sorry, "' + arg + '" contains invalid rule numbers.')
						except IndexError:
							self.say(nick, "Rules " + arg + " could not be parsed. Use commas for singular entries and dashes to designate a range.")
						except KeyError:
							self.say(nick, "Some of rules " + arg + " do not exist.")
		elif args[0] == "new":
			try:
				key = int(args[1].rstrip('.'))
				item = " ".join(args[2:])
				rules = self.getDB()
				rules[key] = item
				self.ruleversions.append("rules/rules " + datetime.now().strftime("%d.%m.%y %H.%M.%S") + ".txt")
				f = open(self.ruleversions[len(self.ruleversions)-1], "w")
				for rule in sorted(rules.items()):
					f.write(str(rule[0]) + ". " + rule[1] + "\n")
				f.close()
			except IndexError:
				self.say(self.channel, "That is not a valid new rule.")
			except ValueError:
				self.say(self.channel, "That is not a valid rule number.")
			else:
				url = "http://dl.dropbox.com/u/14724925/NomicBot/" + self.ruleversions[len(self.ruleversions)-1].replace(" ", "%20")
				self.say(self.channel, "Rule " + str(key) + " has been successfully recorded. URL: " + url)
				self.updateversions()
		elif args[0] == "delete":
			try:
				key = int(args[1].rstrip('.'))
				rules = self.getDB()
				rules.pop(key)
				self.ruleversions.append("rules/rules " + datetime.now().strftime("%d.%m.%y %H.%M.%S") + ".txt")
				f = open(self.ruleversions[len(self.ruleversions)-1], "w")
				for rule in sorted(rules.items()):
					f.write(str(rule[0]) + ". " + rule[1] + "\n")
				f.close()
				url = "http://dl.dropbox.com/u/14724925/NomicBot/" + self.ruleversions[len(self.ruleversions)-1].replace(" ", "%20")
				self.say(self.channel, "Rule " + str(key) + " has been successfully removed. URL: " + url)
			except:
				self.say(self.channel, "Something went wrong. Format = NomicBot, delete <rule#>")
		elif cmd == "revert":
			if len(self.ruleversions) > 1:
				self.ruleversions.pop()
				self.updateversions()
				url = "http://dl.dropbox.com/u/14724925/NomicBot/" + self.ruleversions[len(self.ruleversions)-1].replace(" ", "%20")
				self.say(self.channel, "Successfully reverted back to previous ruleset: " + url)
			else:
				self.say(self.channel, "You are already using the earliest version of the rules.")
		elif cmd == "current":
			self.say(self.channel, "This is the current ruleset: " + "http://dl.dropbox.com/u/14724925/NomicBot/" + self.ruleversions[len(self.ruleversions)-1].replace(" ", "%20"))
		elif args[0] == "points":
			if len(args) == 1:
				self.say(self.channel, "Current points: http://dl.dropbox.com/u/14724925/NomicBot/points.txt")
			elif len(args) == 3:
					try:
						user = args[1]
						self.points[user]
					except KeyError:
						self.points[user] = 0
					self.points[user]+=int(args[2])
					
					f = open("points.txt", "w")
					for p in self.points.items():
						f.write(p[0] + " - " + str(p[1]) + "\n")
					f.close()
					
					self.say(self.channel, "Points updated: " + user + " now has " + str(self.points[user]) + " points.")
			elif len(args) == 4:
				try:
					user = args[2]
					self.points[user]
				except KeyError:
					self.points[user] = 0
				
				if args[1] == "add":
					self.points[user]+=int(args[3])
				elif args[1] == "subtract":
					self.points[user]-=int(args[3])
					
				f = open("points.txt", "w")
				for p in self.points.items():
					f.write(p[0] + " - " + str(p[1]) + "\n")
				f.close()
				
				self.say(self.channel, "Points updated: " + user + " now has " + str(self.points[user]) + " points.")
		elif cmd == "update":
			f = open("users.txt")
			for line in f:
				self.powerusers.append(line.strip("\n"))
			f.close()
		elif cmd == "help":
			self.say(nick, "rule <number> - Says the rule associated with that number in the channel.")
			self.say(nick, "rules <numbers> - PMs you several rules. Will parse ranges(102-105) and singles(102,103,105).")
			self.say(nick, "new <number> <rule text> - Creates a new rule or overwrites the rule number indicated.")
			self.say(nick, "delete <number> - Deletes the rule number indicated.")
			self.say(nick, "points <user> <number> - Adds (or subtracts if the number is negative) points to/from the user. Shows points if said without arguments.")
			self.say(nick, "revert - Reverts the current ruleset to the previous one.")
			self.say(nick, "current - Displays the current ruleset.")
		else:
			self.say(nick, "Not understood: " + cmd)

def main():
	# import sys
	# if len(sys.argv) != 4:
		# print "Usage: testbot <server[:port]> <channel> <nickname>"
		# sys.exit(1)

	# s = sys.argv[1].split(":", 1)
	# server = s[0]
	# if len(s) == 2:
		# try:
			# port = int(s[1])
		# except ValueError:
			# print "Error: Erroneous port."
			# sys.exit(1)
	# else:
		# port = 6667
	# channel = sys.argv[2]
	# nickname = sys.argv[3]

	bot = TestBot("#Nomic", "NomicBot", "irc.mountai.net", 6667)
	bot.start()

if __name__ == "__main__":
	main()
