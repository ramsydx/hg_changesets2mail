#!/usr/bin/env python2.4
# encoding: utf-8
# -*- coding: utf-8 -*-
#

import getopt, sys, os, datetime,re
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

def usage():
	print "Usage: "+os.path.basename(__file__)+" [MUST PARAMS] [OPTION]..."
	print
	print "MUST PARAMS:"
	print "  -f,--from=MAIL         送信元メールアドレスの指定"
	print "  -t,--to=MAIL           送信先メールアドレスの指定"
	print
	print "OPTIONS:"
	print "  -h,--help              このヘルプの表示"
	print "  -d,--debug             実際にはメール送信を行わないフラグのトグル"
	print "  -s,--savefile=FILE     チェック済みチェンジセットの履歴ファイル指定"
	print "  -r,--repository=DIR    mercurialレポジトリの場所"
	print "  -a,--ages=AGES         確認する世代数"

def isMailaddress(addr):
	# http://d.hatena.ne.jp/fgshun/20090204/1233761360
	return (None != re.match(u'(?:[^ <>@,;:".\\\\\\[\\]\x00-\x1f\x80-\uffff]+(?![^ <>@,;:".\\\\\\[\\]\x00-\x1f\x80-\uffff])|"[^\\\\\x80-\uffff\n\r"]*(?:\\\\[^\x80-\uffff][^\\\\\x80-\uffff\n\r"]*)*")(?:\\.(?:[^ <>@,;:".\\\\\\[\\]\x00-\x1f\x80-\uffff]+(?![^ <>@,;:".\\\\\\[\\]\x00-\x1f\x80-\uffff])|"[^\\\\\x80-\uffff\n\r"]*(?:\\\\[^\x80-\uffff][^\\\\\x80-\uffff\n\r"]*)*"))*@(?:[^ <>@,;:".\\\\\\[\\]\x00-\x1f\x80-\uffff]+(?![^ <>@,;:".\\\\\\[\\]\x00-\x1f\x80-\uffff])|\\[(?:[^\\\\\x80-\uffff\n\r\\[\\]]|\\\\[^\x80-\uffff])*\\])(?:\\.(?:[^ <>@,;:".\\\\\\[\\]\x00-\x1f\x80-\uffff]+(?![^ <>@,;:".\\\\\\[\\]\x00-\x1f\x80-\uffff])|\\[(?:[^\\\\\x80-\uffff\n\r\\[\\]]|\\\\[^\x80-\uffff])*\\]))*',addr))

DATEFORMAT = "%Y/%m/%d %H:%M:%S"

DEBUG_FLAG = False
HIST_FILE = '/dev/null'
REPO_DIR = './'
MAXAGES = '20'
MAILFROM = ''
MAILRCPT = ''

try:
	opts,args = getopt.getopt(sys.argv[1:], "hds:r:a:f:t:", ["help", "debug", "savefile=", "repository=", "ages=", "from=" , "to="])
except getopt.GetoptError:
	print "不正なパラメータが指定されています"
	print
	usage()
	sys.exit(1)

for cmd, arg in opts:
	if cmd in ("-h", "--help"):
		usage()
		sys.exit()
	if cmd in ("-d", "--debug"):
		DEBUG_FLAG = not DEBUG_FLAG
	if cmd in ("-s", "--savefile"):
		HIST_FILE = arg
	if cmd in ("-r", "--repository"):
		REPO_DIR = arg
	if cmd in ("-a", "--ages"):
		MAXAGES = arg
	if cmd in ("-f", "--from"):
		MAILFROM = arg
	if cmd in ("-t", "--to"):
		MAILRCPT = arg

# パラメータバリデーション
HIST_DIR = os.path.abspath(os.path.dirname(HIST_FILE))
if True == os.path.isdir(HIST_FILE) or False == os.path.isdir(HIST_DIR):
	print "ヒストリファイルは正しいパスではありません。"
	print
	usage()
	sys.exit(1)
if True == os.path.exists(HIST_FILE) and False == os.access(HIST_FILE, os.W_OK):
	print "ヒストリファイル'"+HIST_FILE+"'に書き込み出来ません"
	print
	usage()
	sys.exit(1)
if False == os.path.exists(HIST_FILE) and False == os.access(HIST_DIR, os.W_OK):
	print "ヒストリファイル'"+HIST_FILE+"'の作成に必要な権限が不足しています"
	print
	usage()
	sys.exit(1)

if False == os.path.isdir(REPO_DIR):
	print "レポジトリはディレクトリを指定する必要があります。"
	print
	usage()
	sys.exit(1)

if False == MAXAGES.isdigit():
	print "世代数は正の整数で指定してください'"+MAXAGES+"'"
	print
	usage()
	sys.exit(1)
MAXAGES = int(MAXAGES)

if '' == MAILFROM:
	print "送信元メールアドレスが指定されていません"
	print
	usage()
	sys.exit(1)
if False == isMailaddress(MAILFROM):
	print "送信元メールアドレスが正しい書式ではありません"
	print
	usage()
	sys.exit(1)

if '' == MAILRCPT:
	print "送信先メールアドレスが指定されていません"
	print
	usage()
	sys.exit(1)
if False == isMailaddress(MAILRCPT):
	print "送信先メールアドレスが正しい書式ではありません"
	print
	usage()
	sys.exit(1)

u = ui.ui()
repo = hg.repository(u, REPO_DIR)

tip = repo.changectx("tip")
tip_rev = tip.rev()

cs=[]
try:
	if os.path.exists(HIST_FILE):
		of=open(HIST_FILE,'rU+')
		changesets=of.readlines()
		of.close()
		for c in changesets:
			cs.append(c.rstrip())
	of=open(HIST_FILE,'wU+')
except IOError:
	print "ヒストリファイル'"+HIST_FILE+"'への書き込みに失敗しました"
	usage()
	sys.exit(1)

for i in range(tip_rev,tip_rev-MAXAGES,-1):
	ctx = repo.changectx(i)
	revisionID = ctx.__str__()
	of.write(revisionID+'\n')
	if revisionID not in cs:
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
		if DEBUG_FLAG:
			print msg
		else:
			send(MAILFROM, MAILRCPT, msg)

of.close()
sys.exit()
