#!/bin/bash

# Ensure correct permissions
chown -R root:root /etc/postfix/*
chmod -R 644 /etc/postfix/*
chmod -R 755 /etc/postfix/postfix-script
chmod -R 755 /var/spool/postfix

# Initialize Postfix
newaliases
postmap /etc/postfix/virtual
postmap /etc/postfix/transport

# Start Postfix in foreground mode
postfix start-fg
