FROM python:3.9-slim
RUN apt-get update && apt-get install -y \
    openjdk-17-jdk wget curl procps \
    && rm -rf /var/lib/apt/lists/*

ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64
ENV SPARK_VERSION=3.5.0
ENV HADOOP_VERSION=3
ENV SPARK_HOME=/opt/spark

RUN wget -q https://archive.apache.org/dist/spark/spark-${SPARK_VERSION}/spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION}.tgz \
    && tar -xzf spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION}.tgz \
    && mv spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION} ${SPARK_HOME} \
    && rm spark-${SPARK_VERSION}-bin-hadoop${HADOOP_VERSION}.tgz

ENV PATH="${SPARK_HOME}/bin:${SPARK_HOME}/sbin:${PATH}"
ENV PYSPARK_PYTHON=python3
RUN wget -q https://repo1.maven.org/maven2/org/apache/spark/spark-sql-kafka-0-10_2.12/${SPARK_VERSION}/spark-sql-kafka-0-10_2.12-${SPARK_VERSION}.jar \
    -O ${SPARK_HOME}/jars/spark-sql-kafka-0-10_2.12-${SPARK_VERSION}.jar

RUN wget -q https://repo1.maven.org/maven2/org/apache/kafka/kafka-clients/3.4.0/kafka-clients-3.4.0.jar \
    -O ${SPARK_HOME}/jars/kafka-clients-3.4.0.jar

RUN wget -q https://repo1.maven.org/maven2/org/apache/commons/commons-pool2/2.11.1/commons-pool2-2.11.1.jar \
    -O ${SPARK_HOME}/jars/commons-pool2-2.11.1.jar

RUN wget -q https://repo1.maven.org/maven2/org/apache/spark/spark-token-provider-kafka-0-10_2.12/${SPARK_VERSION}/spark-token-provider-kafka-0-10_2.12-${SPARK_VERSION}.jar \
    -O ${SPARK_HOME}/jars/spark-token-provider-kafka-0-10_2.12-${SPARK_VERSION}.jar

RUN pip install --no-cache-dir \
    pyspark==3.5.0 \
    jupyterlab==4.0.7 \
    kafka-python==2.0.2 \
    pandas==2.1.1 \
    numpy==1.26.0 \
    matplotlib==3.8.0 \
    seaborn==0.13.0 \
    requests==2.31.0 \
    flask==3.0.0 \
    flask-cors==4.0.0 \
    scikit-learn==1.3.2 \
    scipy==1.11.3

WORKDIR /app

EXPOSE 8080 7077 8888 4040
