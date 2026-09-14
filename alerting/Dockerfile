# Stage 1: build the fat jar with Maven
FROM maven:3.9-eclipse-temurin-17 AS build
WORKDIR /build
COPY pom.xml .
# Download dependencies first so this layer is cached across code-only rebuilds
RUN mvn -B dependency:go-offline
COPY src ./src
RUN mvn -B package -DskipTests=false

# Stage 2: slim runtime image -- no Maven, no build tools, just the JRE + jar
FROM eclipse-temurin:17-jre-alpine
WORKDIR /app
COPY --from=build /build/target/alerting.jar ./alerting.jar

# predictions.csv is mounted in via the shared volume at runtime (see docker-compose.yml)
ENTRYPOINT ["java", "-jar", "alerting.jar", "/data/predictions.csv"]