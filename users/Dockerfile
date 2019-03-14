FROM golang:latest

LABEL Name=users Version=0.0.1

RUN mkdir -p /go/src \
    && mkdir -p /go/bin \
    && mkdir -p /go/pkg

ENV GOPATH=/go
ENV PATH=$GOPATH/bin:$PATH

RUN mkdir -p $GOPATH/src/app
ADD . $GOPATH/src/app

WORKDIR $GOPATH/src/app
RUN go build -o main .

CMD ["./run.sh"]
CMD ["/go/src/app/main"]

EXPOSE 3000
