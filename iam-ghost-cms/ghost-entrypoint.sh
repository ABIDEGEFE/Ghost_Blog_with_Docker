#!/bin/sh

export database__connection__password=$(cat /run/secrets/ghost_db_password)
export mail__options__auth__pass=$(cat /run/secrets/smtp_password)

exec "$@"
