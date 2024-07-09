#!/usr/bin/env python

import sys, urllib.request, email, re, csv, base64, json, pprint, os
import pymysql
from dbutils.pooled_db import PooledDB
from optparse import OptionParser
from io import StringIO
from datetime import datetime
import logging

VERSION = "1.3.2"
output_folder = "/tmp/"
email_re = re.compile(r"(^[-!#$%&'*+/=?^_`{}|~0-9A-Z]+(\.[-!#$%&'*+/=?^_`{}|~0-9A-Z]+)*)@((?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)$|\[(25[0-5]|2[0-4]\d|[0-1]?\d?\d)(\.(25[0-5]|2[0-4]\d|[0-1]?\d?\d)){3}\]$)", re.IGNORECASE)
email_extract_re = re.compile(r"<(([.0-9a-z_+-=]+)@(([0-9a-z-]+\.)+[0-9a-z]{2,9}))>", re.M | re.S | re.I)
filename_re = re.compile(r"filename=\"(.+)\"|filename=([^;\n\r\"\']+)", re.I | re.S)
begin_tab_re = re.compile(r"^\t{1,}", re.M)
begin_space_re = re.compile(r"^\s{1,}", re.M)

# Setup logging
logging.basicConfig(level=logging.DEBUG, filename="/tmp/email_processor.log", filemode="a",
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# Database connection pool
pool = PooledDB(
    creator=pymysql,
    host='',
    user='',
    password='!',
    database='emails',
    autocommit=True,
    charset='utf8mb4',
    cursorclass=pymysql.cursors.DictCursor,
    blocking=True,
    maxconnections=5
)

class MailJson:
    def __init__(self, content=None):
        self.data = {}
        self.raw_parts = []
        self.encoding = "utf-8"  # output encoding
        self.setContent(content)

    def setEncoding(self, encoding):
        self.encoding = encoding

    def setContent(self, content):
        self.content = content

    def _fixEncodedSubject(self, subject):
        if subject is None:
            return ""
        subject = "%s" % subject
        subject = subject.strip()
        if len(subject) < 2:
            return subject
        if subject.find("\n") == -1:
            return subject
        if subject[0:2] != "=?":
            return subject
        subject = subject.replace("\r", "")
        subject = begin_tab_re.sub("", subject)
        subject = begin_space_re.sub("", subject)
        lines = subject.split("\n")
        new_subject = ""
        for l in lines:
            new_subject = "%s%s" % (new_subject, l)
            if l[-1] == "=":
                new_subject = "%s\n " % new_subject
        return new_subject

    def _extract_email(self, s):
        ret = email_extract_re.findall(s)
        if len(ret) < 1:
            p = s.split(" ")
            for e in p:
                e = e.strip()
                if email_re.match(e):
                    return e
            return None
        else:
            return ret[0][0]

    def _decode_headers(self, v):
        if type(v) is not list:
            v = [v]
        ret = []
        for h in v:
            h = email.header.decode_header(h)
            h_ret = []
            for h_decoded in h:
                hv = h_decoded[0]
                h_encoding = h_decoded[1]
                if h_encoding is None:
                    h_encoding = "ascii"
                else:
                    h_encoding = h_encoding.lower()
                if isinstance(hv, bytes):
                    hv = str(hv)
                hv = str(hv.encode(self.encoding), h_encoding).strip().strip("\t")
                h_ret.append(hv.encode(self.encoding))
            ret.append(str(b" ".join(h_ret), self.encoding))
        return ret

    def _parse_recipients(self, v):
        if v is None:
            return None
        ret = []
        if isinstance(v, list):
            v = ",".join(v)
        v = v.replace("\n", " ").replace("\r", " ").strip()
        s = StringIO(v)
        c = csv.reader(s)
        try:
            row = next(c)
        except StopIteration:
            return ret
        for entry in row:
            entry = entry.strip()
            if email_re.match(entry):
                e = entry
                entry = ""
            else:
                e = self._extract_email(entry)
                entry = entry.replace("<%s>" % e, "")
                entry = entry.strip()
                if e and entry.find(e) != -1:
                    entry = entry.replace(e, "").strip()
            if entry and e is None:
                e_split = entry.split(" ")
                e = e_split[-1].replace("<", "").replace(">", "")
                entry = " ".join(e_split[:-1])
            ret.append({"name": entry, "email": e})
        return ret

    def _parse_date(self, v):
        if v is None:
            return datetime.now()
        tt = email.utils.parsedate_tz(v)
        if tt is None:
            return datetime.now()
        timestamp = email.utils.mktime_tz(tt)
        date = datetime.fromtimestamp(timestamp)
        return date

    def _get_part_headers(self, part):
        headers = {}
        for k in list(part.keys()):
            k = k.lower()
            v = part.get_all(k)
            v = self._decode_headers(v)
            if len(v) == 1:
                headers[k] = v[0]
            else:
                headers[k] = v
        return headers

    def parse(self):
        self.msg = email.message_from_string(self.content)
        content_charset = self.msg.get_content_charset()
        if content_charset is None:
            content_charset = 'utf-8'
        headers = self._get_part_headers(self.msg)
        self.data["headers"] = headers
        self.data["datetime"] = self._parse_date(headers.get("date", None)).strftime("%Y-%m-%d %H:%M:%S")
        self.data["subject"] = self._fixEncodedSubject(headers.get("subject", None))
        self.data["to"] = self._parse_recipients(headers.get("to", None))
        self.data["reply-to"] = self._parse_recipients(headers.get("reply-to", None))
        self.data["from"] = self._parse_recipients(headers.get("from", None))
        self.data["cc"] = self._parse_recipients(headers.get("cc", None))
        attachments = []
        parts = []
        for part in self.msg.walk():
            if part.is_multipart():
                continue
            content_disposition = part.get("Content-Disposition", None)
            if content_disposition:
                r = filename_re.findall(content_disposition)
                if r:
                    filename = sorted(r[0])[1]
                else:
                    filename = "undefined"
                a = {"filename": filename, "content": base64.b64encode(part.get_payload(decode=True)), "content_type": part.get_content_type()}
                attachments.append(a)
            else:
                try:
                    p = {"content_type": part.get_content_type(), "content": str(part.get_payload(decode=1), content_charset, "ignore"), "headers": self._get_part_headers(part)}
                    parts.append(p)
                    self.raw_parts.append(part)
                except LookupError:
                    pass
        self.data["attachments"] = attachments
        self.data["parts"] = parts
        self.data["encoding"] = self.encoding
        return self.get_data()

    def get_data(self):
        return self.data

    def get_raw_parts(self):
        return self.raw_parts

def insert_email_data(data):
    conn = pool.connection()
    try:
        with conn.cursor() as cursor:
            sql_email = """
            INSERT INTO emails (received_time, subject, from_email, from_name, reply_to_email, reply_to_name,
                                to_email, to_name, cc_email, cc_name, raw_headers, encoding)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            from_data = data['from'][0] if data['from'] else {'email': None, 'name': None}
            reply_to_data = data['reply-to'][0] if data['reply-to'] else {'email': None, 'name': None}
            to_data = data['to'][0] if data['to'] else {'email': None, 'name': None}
            cc_data = data['cc'][0] if data['cc'] else {'email': None, 'name': None}

            cursor.execute(sql_email, (
                data['datetime'], data['subject'],
                from_data['email'], from_data['name'],
                reply_to_data['email'], reply_to_data['name'],
                to_data['email'], to_data['name'],
                cc_data['email'], cc_data['name'],
                json.dumps(data['headers']), data['encoding']
            ))

            email_id = cursor.lastrowid

            sql_parts = """
            INSERT INTO email_parts (email_id, headers, content_type, content)
            VALUES (%s, %s, %s, %s)
            """
            parts_data = [(email_id, json.dumps(part['headers']), part['content_type'], part['content']) for part in data['parts']]
            cursor.executemany(sql_parts, parts_data)

            sql_attachments = """
            INSERT INTO email_attachments (email_id, filename, content_type, content)
            VALUES (%s, %s, %s, %s)
            """
            attachments_data = [(email_id, attachment['filename'], attachment['content_type'], base64.b64decode(attachment['content'])) for attachment in data['attachments']]
            cursor.executemany(sql_attachments, attachments_data)

        conn.commit()
    except Exception as e:
        logging.error("Failed to insert email data: %s", e)
        conn.rollback()
    finally:
        conn.close()

def main():
    parser = OptionParser(usage="usage: %prog [options]", version="%prog " + VERSION)
    parser.add_option("-f", "--file", dest="filename", help="read content from FILE", metavar="FILE")
    parser.add_option("-u", "--url", dest="url", help="download content from URL")
    parser.add_option("-o", "--output", dest="output", help="output folder", default=output_folder)
    parser.add_option("-c", "--config", dest="config", help="config file", metavar="CONFIG")
    parser.add_option("-e", "--encoding", dest="encoding", help="output encoding")
    (options, args) = parser.parse_args()

    logging.info("Starting email processing")

    content = None
    if options.filename:
        logging.info("Reading content from file: %s", options.filename)
        with open(options.filename, "r") as f:
            content = f.read()
    elif options.url:
        logging.info("Downloading content from URL: %s", options.url)
        content = urllib.request.urlopen(options.url).read()
    else:
        logging.info("Reading content from stdin")
        content = sys.stdin.read()

    if options.encoding:
        logging.info("Setting encoding to: %s", options.encoding)

    mj = MailJson(content)
    if options.encoding:
        mj.setEncoding(options.encoding)

    email_data = mj.parse()
    logging.debug("Parsed email data: %s", email_data)

    insert_email_data(email_data)

    output_file = os.path.join(options.output, "email.json")
    with open(output_file, "w") as f:
        f.write(json.dumps(email_data, indent=4))
        logging.info("Email data written to: %s", output_file)

    logging.info("Email processing completed")

if __name__ == "__main__":
    main()
