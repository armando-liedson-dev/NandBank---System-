FROM eclipse-temurin:21-jdk-alpine
WORKDIR /app
COPY src/main/java/mz/globalscale/LegacyServer.java /src/LegacyServer.java
RUN mkdir -p /app/classes && javac --add-modules jdk.httpserver -encoding UTF-8 -d /app/classes /src/LegacyServer.java
EXPOSE 8090
CMD ["sh", "-c", "keytool -importcert -file /certs/ca.crt -alias globalscale-ca -keystore /tmp/truststore.p12 -storetype PKCS12 -storepass \"$CERT_PASSWORD\" -noprompt >/dev/null 2>&1 && exec java --add-modules jdk.httpserver -cp /app/classes mz.globalscale.LegacyServer"]
