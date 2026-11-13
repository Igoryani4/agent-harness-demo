FROM maven:3.9-eclipse-temurin-17

RUN mkdir -p /tmp/warmup && cd /tmp/warmup && \
    cat > pom.xml <<'POM'
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <groupId>warm</groupId>
  <artifactId>warm</artifactId>
  <version>1.0</version>
  <properties>
    <maven.compiler.source>17</maven.compiler.source>
    <maven.compiler.target>17</maven.compiler.target>
    <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
  </properties>
  <dependencies>
    <dependency>
      <groupId>org.slf4j</groupId>
      <artifactId>slf4j-api</artifactId>
      <version>2.0.9</version>
    </dependency>
    <dependency>
      <groupId>org.springframework</groupId>
      <artifactId>spring-context</artifactId>
      <version>6.1.3</version>
    </dependency>
    <dependency>
      <groupId>org.junit.jupiter</groupId>
      <artifactId>junit-jupiter</artifactId>
      <version>5.10.0</version>
      <scope>test</scope>
    </dependency>
  </dependencies>
  <build>
    <plugins>
      <plugin>
        <groupId>org.apache.maven.plugins</groupId>
        <artifactId>maven-surefire-plugin</artifactId>
        <version>3.2.2</version>
      </plugin>
    </plugins>
  </build>
</project>
POM

RUN cd /tmp/warmup && mvn -q dependency:go-offline
RUN mkdir -p /tmp/warmup/src/test/java && \
    echo 'public class SmokeTest {}' > /tmp/warmup/src/test/java/SmokeTest.java && \
    cd /tmp/warmup && mvn -q test || true

RUN mkdir -p /opt/m2-seed && cp -r /root/.m2/. /opt/m2-seed/

RUN useradd -m sandboxuser
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

USER sandboxuser
WORKDIR /workspace
ENTRYPOINT ["/entrypoint.sh"]
