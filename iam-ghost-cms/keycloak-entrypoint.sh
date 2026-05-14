#!/bin/sh

# Read DB password from secret
export KC_DB_PASSWORD=$(cat /run/secrets/keycloak_db_password)

# Read admin password
export KEYCLOAK_ADMIN_PASSWORD=$(cat /run/secrets/keycloak_admin_password)

# Start Keycloak
exec /opt/keycloak/bin/kc.sh start
