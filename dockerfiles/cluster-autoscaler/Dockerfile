FROM golang:1.17.7 as builder

ARG AUTOSCALER_VERSION

ENV GOPATH=/go

WORKDIR $GOPATH/src/k8s.io/
RUN git clone -b ${AUTOSCALER_VERSION} --single-branch http://github.com/kubernetes/autoscaler.git autoscaler
WORKDIR autoscaler/cluster-autoscaler
RUN CGO_ENABLED=0 GO111MODULE=off GOOS=linux go build -o cluster-autoscaler --ldflags=-s --tags magnum

FROM gcr.io/distroless/static:latest

COPY --from=builder /go/src/k8s.io/autoscaler/cluster-autoscaler/cluster-autoscaler /cluster-autoscaler
CMD ["/cluster-autoscaler"]
