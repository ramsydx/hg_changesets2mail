#!/usr/bin/env python2.4
# encoding: utf-8
# -*- coding: utf-8 -*-
#

import datetime
import smtplib
from email.MIMEText import MIMEText
from email.Header import Header
from email.Utils import formatdate
from mercurial import ui, hg, cmdutil, patch

def send(from_addr, to_addr, msg):
	s = smtplib.SMTP('localhost')
	s.sendmail(from_addr, [to_addr], msg.as_string())
	s.close()

def create_message_mime(from_addr, to_addr, subject, body, encoding):
	msg = MIMEText(body, 'plain', encoding)
	msg['Subject'] = Header(subject, encoding)
	msg['From'] = from_addr
	msg['To'] = to_addr
	msg['Date'] = formatdate()
	return msg

HIST_FILE = '/var/tmp/changesets'
REPO_DIR = './'
MAILRCPT = 'SET HERE : RCPT MAIL ADDRESS'
MAILFROM = 'SET HERE : FROM MAIL ADDRESS'
MAXAGES = 20
DATEFORMAT = "%Y/%m/%d %H:%M:%S"

u = ui.ui()
repo = hg.repository(u, REPO_DIR)

tip = repo.changectx("tip")
tip_rev = tip.rev()

cs=[]
try:
	of=open(HIST_FILE,'rU+')
	changesets=of.readlines()
	for c in changesets:
		cs.append(c.rstrip())
except IOError:
	of=open(HIST_FILE,'wU+')


for i in range(tip_rev,tip_rev-MAXAGES,-1):
	ctx = repo.changectx(i)
	revisionID = ctx.__str__()
	if revisionID not in cs:
		of.write(revisionID+'\n')
		ft = datetime.datetime.fromtimestamp(ctx.date()[0]).strftime(DATEFORMAT)
		body  = "チェンジセット\n    "+str(i)+':'+revisionID+'\n'
		body += "ユーザ\n    "+ctx.user()+'\n'
		body += "日付\n    "+ft+'\n'
		files_stat = repo.status(ctx.parents()[0], ctx, clean=True)
		for i,name in enumerate(['更新','新規','削除']):
			if len(files_stat[i]):
				body += 'ファイル('+name+')\n'
				for f in files_stat[i]:
					body += "    "+f+'\n'
		body += "説明\t"+'\n'
		body += ctx.description()
		descs = ctx.description().split('\n')
		subject = '[KikyoUpdate]:'
		for s in descs:
			if len(s) > 0:
				if s[0] == '*':
					subject+=s[1:]
		msg = create_message_mime(MAILFROM,MAILRCPT,subject,body,'UTF-8')
		send(MAILFROM, MAILRCPT, msg)
		#print msg

of.close()
