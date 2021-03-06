# Generated by the gRPC Python protocol compiler plugin. DO NOT EDIT!
import grpc

from stub import hello_pb2 as hello__pb2


class HelloServiceStub(object):
  # missing associated documentation comment in .proto file
  pass

  def __init__(self, channel):
    """Constructor.

    Args:
      channel: A grpc.Channel.
    """
    self.SayHello = channel.unary_unary(
        '/hello.HelloService/SayHello',
        request_serializer=hello__pb2.HelloReq.SerializeToString,
        response_deserializer=hello__pb2.HelloResp.FromString,
        )
    self.SayHelloStrict = channel.unary_unary(
        '/hello.HelloService/SayHelloStrict',
        request_serializer=hello__pb2.HelloReq.SerializeToString,
        response_deserializer=hello__pb2.HelloResp.FromString,
        )


class HelloServiceServicer(object):
  # missing associated documentation comment in .proto file
  pass

  def SayHello(self, request, context):
    """This thing just says Hello to anyone
    SayHello('Euler') -> Hello, Euler!
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')

  def SayHelloStrict(self, request, context):
    """Strict Version responds only to requests which have `Name` length
    less than 10 characters
    """
    context.set_code(grpc.StatusCode.UNIMPLEMENTED)
    context.set_details('Method not implemented!')
    raise NotImplementedError('Method not implemented!')


def add_HelloServiceServicer_to_server(servicer, server):
  rpc_method_handlers = {
      'SayHello': grpc.unary_unary_rpc_method_handler(
          servicer.SayHello,
          request_deserializer=hello__pb2.HelloReq.FromString,
          response_serializer=hello__pb2.HelloResp.SerializeToString,
      ),
      'SayHelloStrict': grpc.unary_unary_rpc_method_handler(
          servicer.SayHelloStrict,
          request_deserializer=hello__pb2.HelloReq.FromString,
          response_serializer=hello__pb2.HelloResp.SerializeToString,
      ),
  }
  generic_handler = grpc.method_handlers_generic_handler(
      'hello.HelloService', rpc_method_handlers)
  server.add_generic_rpc_handlers((generic_handler,))
