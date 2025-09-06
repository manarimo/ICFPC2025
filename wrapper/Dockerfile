FROM golang:1.25

COPY . /app/
WORKDIR /app
RUN go build

CMD ["./wrapper", "/to-wrapper", "/from-wrapper"]