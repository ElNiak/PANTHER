# Introduction

Modular specifications have uses other than verification. Imagine that
we have formal interface specifications of all of the components of a
system. A formal argument tells us that, if all the component
implementations satisfy their specifications, then the system as a
whole satisfies its specification. However, we don't yet have formal
proofs that the component implementations are correct.

In this scenario we can use *compositional testing* to improve our
confidence in the system's correctness. We test each
component rigorously against its formal specification. If we have high
confidence in the correctness of all of the components, this
confidence transfers to the system as a whole because of our formal
proof. Put another way, if the system as a whole fails to satisfy its
specification, then necessarily one of its components fails its
specification and we can discover this fact by component testing.

The question is, how can we test the components rigorously in a way
that will give us high confidence of their correctness? One
possibility is to use a *constrained random* approach. That is, we
automatically generate test inputs for the component in a way that
satisfies its interface assumptions. We then check that the component's outputs
satisfy its interface guarantees. The purpose of randomness is to avoid bias
that might creep into a manually generated test suite or testbench.

Ivy can do just that. It can extract a component and a randomized test
environment for that component.  The test environment generates inputs
for the component, calling its exported actions with input parameters
that satisfy the component's assumptions. It also checks that all the
component outputs satisfy the component's guarantees.

This sort of rigorous component-based testing combines the advantages
of unit testing and integration testing. Like informal unit testing,
the method has the advantage that the component's inputs can be
controlled directly. This gives us much more flexibility to cover the
component's "corner cases" and to expose design errors. Unlike
informal unit testing, however, the method uses only the component's
specification, eliminating the possibility of human bias, and giving a
definitive reference for evaluating the test results. Like integration
testing, compositional testing allows us to gain confidence in the
correctness of the system as a whole. Compositional testing can be
much faster, however, because it takes many fewer steps to stimulate a
component bug through the component's interface rather than through
the system's interface. In addition, of course, we do not have to
execute the entire system to test it compositionally.

In the next few sections, we'll run through the same examples we
looked at with [compositional formal verification](specification.md), but instead we'll
use compositional testing.

# Specifications

Formal verification is primarily about establishing relationships
between specifications at differing levels of abstraction. The same
can be said of compositional testing. The difference is that in the
compositional testing approach, we combine formal proof with
specification-based testing to increase our confidence in the
correctness of a system.


Consider, for example, a network protocol, such as the [TCP
protocol](https://en.wikipedia.org/wiki/Transmission_Control_Protocol)
that is widely used to communicate streams of data over the Internet.
At a high level of abstraction, TCP is a *service*, providing methods
for establishing connections, and sending or receiving data. This
service provides guarantees to its users of reliable in-order
transmission of streams of bytes. At a lower level of abstraction, TCP
can be seen as a *protocol*. The protocol is a set of rules (laid out
in [RFC 675](https://tools.ietf.org/html/rfc675) and later documents)
that implements service guarantees of TCP by exchanging datagrams over
an unreliable network.

The service and protocol specifications of TCP are views of the same
process observed at different interfaces. That is, TCP is sandwiched
between a higher-level application (say, a web browser and web server)
and the lower-level datagram protocol (typically the IP protocol) as shown below:

<p><img src="network_stack1.png" alt="Network Stack" /></p>

The TCP service specification describes the events we observe at the
interface between the application layer and the transport layer.  The
IP service specification describes the events we observe at the
interface between the transport layer and the network layer.  The TCP
protocol specification describes the *relation* between events at this
interface and the lower-level interface between transport and network
layers.

If we were developing the TCP protocol specification, we would like to
verify that the IP service and the TCP protocol together implement the
TCP service specification. That is, if events at the transport/network
interface are consistent with the IP service specification, and if we
execute the TCP protocol according to its specification, then events
at the application/transport interface should be consistent with the TCP
service specification. From the point of view of the TCP protocol, we
say that the IP service specification is an *assumption*, while the
TCP service specification is a *guarantee*. 

IVy has features that allow us to combine testing with formal
verification to perform this kind of reasoning. It allows us to:

- Define objects with interfaces
- Write specifications about interfaces
- Test assume/guarantee relationships between these specifications

In IVy, interfaces and specifications are objects. An interface is
an object with unimplemented actions (a bit like an instance of an
abstract class in C++). A specification is a special object that
monitors the calls and returns across an interface and makes assertions
about their correctness.

### Monitors as specifications

To specify services such as TCP, we need to make assertions about the
*sequences* of events that can occur at an interface. For example, in
TCP, we need to make statements relating the sequences of send and
receive events to abstract data streams that are transmitted between
clients. Specifications about sequences of events in time are often
referred to as *temporal* specifications.

A common approach to temporal specification is to define a specialized
logical notation called a [*temporal
logic*](http://plato.stanford.edu/entries/logic-temporal). These
notations make it possible to write succinct temporal specifications,
and also us to do some proofs in a fully automated way using [model
checking](http://www.loria.fr/~merz/papers/mc-tutorial.pdf).

IVy takes a different approach.  Temporal specifications in IVy are
defined using special objects called *monitors*. A monitor is an
object that synchronizes its actions with calls and returns across an
interface. This allows the monitor to record information about the
history of the interface in its local state, and to assert facts that
should be true about interface events based on the history of previous
events.

As an example, here is a definition of an interface for a ridiculously
simple network service:
 
    #lang ivy1.6
    type packet

    object intf = {
        action send(x:packet)
        action recv(x:packet)
    }

The type `packet` is an example of an [*uninterpreted type*](../../language.html#declarations). We don't
yet know want the contents of a packet are, but we can fill in the
definition of `packet` later.

The actions in an interface object don't have definitions. These will
be filled in by other objects that implement the different roles in
the interface. We don't know yet what these objects actually do, but
we can write a service specification that tells us something about the
temporal behavior at the interface:

    object spec = {
        relation sent(X:packet)

        after init {
            sent(X) := false
        }

        before intf.send {
            sent(x) := true
        }

        before intf.recv {
            assert sent(x)
        }
    }

Object `spec` is a monitor. It has one local state component `sent`
that records the set of packets that have been sent so far.  The
`after init` declaration says that, initially, no packet `X` has been sent.
In [the Ivy language](../../language.html), symbols beginning with
capital letters are logical variables. Unbound variables are
implicitly universally quantified.

Information about sent packets is recorded by inserting an action
*before* every call to `intf.send`. This is done using a `before`
declaration in the specification. Notice that the inserted action can
refer to the parameters of `intf.send` and it can update the monitor
state.  In addition, the monitor inserts an assertion before every
call to `intf.recv`. This assertion states that the received packet
`x` has previously been sent.

In effect, our service specification describes a channel that can
re-order and duplicate packets, but cannot corrupt packets. If any
corrupted packet is received, the assertion will fail.

Now let's consider some possible implementations of this very simple
specification. Here is the most trivial one:

    object protocol = {
        implement intf.send {
            call intf.recv(x)
        }
    }

Object `protocol` provides the implementation of action `intf.send`
using an `implement` declaration. This declaration provides the
missing body of the action `intf.send`. The implementation simply calls `intf.recv`
on the sent packet `x`. The assertion in monitor `spec` is always
true, since before calling `intf.send`, the packet `x` is added to the
relation `sent`. That is, our implementation trivially satisfies the
specification "receive only sent packets".

To verify our implementation, we need to put it in a suitable
environment. The following statements tell us that the environment
will implement `intf.recv` and will call `intf.send`:

    import intf.recv
    export intf.send

In order to test our program, we need to give a concrete interpretation to
the abstract type `packet`. It doesn't much matter what this interpretation is.
This statement tells IVy to represent packets using 16-bit binary numbers:

    interpret packet -> bv[16]

Now, let's do some verification. The IVy compiler can translate our
program into C++, and also generate a randomized tester that takes the
role of the environment. We save the above text to the file
`trivnet.ivy`, then compile like this:

    $ ivy_to_cpp target=test build=true trivnet.ivy
    g++ -I $Z3DIR/include -L $Z3DIR/lib -g -o trivnet trivnet.cpp -lz3

The command line options tell `ivy_to_cpp` to generate a test environment
and to use the C++ compiler to generate an executable file. When we run the
executable, the output looks like this:

    ./trivnet
    > intf.send(61468)
    < intf.recv(61468)
    > intf.send(49878)
    < intf.recv(49878)
    > intf.send(18736)
    < intf.recv(18736)
    > intf.send(41051)
    < intf.recv(41051)
    ...

The output lines beginning with `>` represent calls from the test
environment into the system, while lines beginning with `<` are calls
from the system into the environment. The specification monitor is
checking that every call to `intf.recv` corresponds to some previous
call to `intf.send`. This input values are just random 16-bit
numbers. Since our implementation is correct, no errors are flagged.

To get a better idea of what is happening with `before` and
`implements`, we can print out the program that results from inserting
the monitor actions and interface implementations. Here is part of the output:

    $ ivy_show trivnet.ivy

    type packet
    relation spec.sent(V0:packet)

    after init {
        spec.sent(X) := false
    }
    action intf.recv(x:packet) = {
        assert spec.sent(x)
    }
    action intf.send(x:packet) = {
        spec.sent(x) := true;
        call intf.recv(x)
    }

Notice that the `before` actions of `spec` have been inserted at the
beginning of these actions, and the `implement` action of `protocol`
has been used as the body of `intf.send`.

Of course, we might consider a (slightly) less trivial implementation,
such as this one that implements the service specification with a
one-place buffer:

    object protocol = {
        individual full : bool
        individual contents : packet
        after init {
            full := false
        }

        implement intf.send {
            full := true;
            contents := x
        }

        action async = {
            if full {
                full := false;
                call intf.recv(contents)
            }
        }
    }

This implementation has an action `async` that needs to be called by the
environment, so we add:

    export protocol.async

The output from the tester looks like this:

    ./trivnet2
    > intf.send(59132)
    > intf.send(18535)
    > protocol.async()
    < intf.recv(18535)
    > intf.send(11708)
    > intf.send(15030)
    > protocol.async()
    < intf.recv(15030)
    > intf.send(64574)
    > intf.send(23863)
    > intf.send(63393)
    > protocol.async()
    < intf.recv(63393)

The tester is calling `intf.send` and `protocol.async` uniformly at
random (with a probability of 0.5 for each). We can see that some
packets (for example the first) are dropped.

Let's put a bug in the protocol to see what happens. The action
`bug` below corrupts the packet buffer:

        action bug(p:packet) = {
            contents := p
        }

    ...
 
    export protocol.bug

Here's a test run:

    ./trivnet3
    > protocol.async()
    > protocol.async()
    > intf.send(18535)
    > protocol.bug(61184)
    > intf.send(31188)
    > intf.send(18749)
    > protocol.async()
    < intf.recv(18749)
    > protocol.bug(6178)
    > intf.send(28724)
    > protocol.bug(45283)
    > protocol.bug(6070)
    > protocol.bug(2590)
    > protocol.bug(10158)
    > protocol.async()
    trivnet3.ivy: line 22: : assertion failed

At some point, the environment calls `bug` then `async` causing the
protocol to deliver a wrong packet value. We can see that the
specification monitor is in fact running, and it gives an error
message pointing to the line in the code where an assertion failed.

### Assume-Guarantee reasoning in IVy

In the previous example, we saw that a service specification is a kind
of abstraction. It hides details of the underlying implementation,
telling us only what we need to know to use the service. Abstractions
are crucial in reasoning about complex systems. They allow us to
develop one component of a system without thinking about the details
of the implementation of other components. For example, when
developing a network application based on TCP, we don't have to read
RFC 675. We just rely on the simple service guarantee that TCP
provides (reliable, in-order delivery). The service specification
allows us to think about our application in *isolation* from the
network protocol stack.

IVy provides a mechanism to do just this when proving correctness of
system components. That is, we can isolate a single object in our
system and prove its correctness using only the service specifications
of its interfaces.

As an example, let's build a system of two components that plays a
highly simplified game of ping-pong. Here is the interface definition:

    #lang ivy1.6

    object intf = {
        action ping
        action pong
    }

Here is the interface specification:

    type side_t = {left,right}

    object spec = {
        individual side : side_t
        after init {
            side := left
        }

        before intf.ping {
            assert side = left;
            side := right
        }

        before intf.pong {
            assert side = right;
            side := left
        }
    }

The specification has a single state component `side` that keeps track
of whether the ball is on the left- or right-hand side of the
table. When the ball is on the left, a `ping` action is allowed,
sending the ball to the right-hand side.  When the ball is on the
right, a `pong` is allowed, sending the ball to the left again.  A
failure to alternate `ping` and `pong` would cause one of the
assertions to fail.

Now let's implement the left-hand player:

    object left_player = {
        individual ball : bool
        after init {
            ball := true
        }

        action hit = {
            if ball {
                call intf.ping;
                ball := false
            }
        }

        implement intf.pong {
            ball := true
        }

    }

The player has a Boolean `ball` that indicates the ball is in the
player's court. We assume the left player serves, so `ball` is
initially true. If the left player has the ball, the `hit` action
will call `ping`, sending the ball to the right, and set `ball` to false.  The
left player implements `ping` by setting `ball` to true.

The right-hand player is similar:

    object right_player = {
        individual ball : bool
        after init {
            ball := false
        }

        action hit = {
            if ball {
                call intf.pong;
                ball := false
            }
        }

        implement intf.ping {
            ball := true
        }

    }

Let's export the `hit` actions to the environment, so the players
will do something:

    export left_player.hit
    export right_player.hit

Here is the call graph of the system we have defined:

<p><img src="pingpong_fig1-crop-1.png" alt="Ping Pong Call Graph" /></p>

Now what we want to do is to generate testers for the left and right
players in isolation. That is, we want the tester for the left player
to act as its environment. This means the tester has to call both
`left_player.hit` and `intf.pong`. Similarly, the tester for the right
player has to call `right_player.hit` and `intf.ping`. 

To generate these testers, we use `isolate` declarations:

    isolate iso_l = left_player with spec
    isolate iso_r = right_player with spec

The first says to isolate the left player using the interface
specification `spec`.  The second says to do the same thing with the
right player. This reduces the system verification problem to two
separate verification problems called "isolates".

Here's the call graph for the left player isolate `iso_l`:

<p><img src="pingpong_fig2-crop-1.png" alt="Ping Pong Call Graph 2" /></p>

We can see what the first isolate looks like textually as follows (leaving a few
things out):

    $ ivy_show isolate=iso_l pingpong.ivy

    individual spec.side : side_t
    relation left_player.ball

    action ext:left_player.hit = {
        if left_player.ball {
            call intf.ping;
            left_player.ball := false
        }
    }

    action intf.ping = {
        assert spec.side = left;
        spec.side := right
    }

    action ext:intf.pong = {
        assume spec.side = right;
        spec.side := left;
        left_player.ball := true
    }

Several interesting things have happened here. First, notice the
action `intf.ping`. We see that the code inserted by `spec` is
present, but the implementation provided by `right_player` is missing.
In effect, the right player has been abstracted away: we see neither
its state nor its actions.  Further, notice that the action `pong` has
been exported to the environment. It contains the monitor code from
`spec` and also the left player's implementation of `pong`. There is a
crucial change, however: the `assert` in the specification of `pong`
has changed to `assume`.

This is an example of *assume-guarantee* reasoning. The left player
*guarantees* to call `ping` only when the ball is on the
left. However, it *assumes* that the right player only calls `pong`
when the ball is on the right. This is a very common situation in protocols. 
Each participant in the protocol guarantees correctness of its outputs,
but only so long as its inputs are correct.

Let's start by testing the left player. First, we compile a tester:

    $ ivy_to_cpp isolate=iso_l target=test build=true pingpong.ivy 
    g++ -I $Z3DIR/include -L $Z3DIR/lib -g -o pingpong pingpong.cpp -lz3

Notice we specified the isolate `iso_l` on the command line.  Now
let's run `pingpong`:

    $ ./pingpong
    > left_player.hit()
    < intf.ping
    > left_player.hit()
    > intf.pong()
    > left_player.hit()
    < intf.ping
    > left_player.hit()
    > intf.pong()
    > left_player.hit()
    < intf.ping
    ...

We can see that the environment (the calls marked with `>`) is
respecting the assumption of the left player that `pong` occurs only
when the ball is on the right, that is, after a `ping`. The tester is
sampling uniformly out of just the actions that satisfy the isolate's
assumptions. You may notice that sometimes the environment calls `hit`
when the left player doesn't have the ball. This is not a problem,
since a `hit` has no effect in this case. What if we neglected to test whether the left player in fact has the ball in the implementation?
Let's try it. That is, let's use this version of the left player's `hit` action:

    action hit = {
        call intf.ping;
        ball := false
    }

Here's what we get:

    $ ./pingpong_bad
    > left_player.hit()
    < intf.ping
    > left_player.hit()
    pingpong_bad.ivy: line 15: : assertion failed

The left player hits when it shouldn't and causes a failure of the
precondition of `ping`.

Now let's consider try right player. We compile and run a tester for
the isolate `iso_r`:

    $ ivy_to_cpp isolate=iso_r target=test build=true pingpong.ivy 
    g++ -I $Z3DIR/include -L $Z3DIR/lib -g -o pingpong pingpong.cpp -lz3
    $ ./pingpong
    > right_player.hit
    > right_player.hit
    > right_player.hit
    > intf.ping
    > right_player.hit
    < intf.pong
    > right_player.hit
    > intf.ping
    > right_player.hit
    < intf.pong
    > intf.ping

Here we see that the testing environment is generating calls to `ping`
and right_player.hit. The `ping` calls satisfy the precondition of
`ping`, that is, `ping` is only called when the ball is on the left
side. The specification monitor is checking that the `pong` calls
generated by the right player satisfy the precondition of `pong`.

So what have we done so far? We've verified by randomized testing the
the left player guarantees correct pings assuming correct pongs. We've
also verified by testing that the right player guarantees correct pongs
given correct pings. Since neither the pings nor the pongs can be the
first to fail, we can conclude that all pings and pongs are correct
according to the specification.

We can ask IVY to check this conclusion for us:

    $ ivy_check trusted=true pingpong.ivy 
    Checking isolate iso_l...
    Checking isolate iso_r...
    OK

The option `trusted=true` tells IVy to trust that the specified
isolates are correct, facts that we have tested, but not formally
verified. IVy says it can prove based on this assumption that all of
our assertions are true at all times.

## Is this really a proof?

In creating the two isolates `iso_l` and `iso_r`, we reduced a proof
goal to two simpler sub-goals. In theorem provers, this kind of
reduction is called a *tactic*.  We must take care that our tactics
are logically sound. That is, is the two sub-goals are provable, then
the original goal must also be provable.

Let's try informally to justify the soundness of our tactic. Ivy
performed two transformations to produce each isolate: it changed some
assertions to assumptions, and it deleted the actions and state components of
one of the two players.

# Pseudo-circular proofs

At first blush, changing assertions to assumptions seems to be unsound
because of a logical circularity. That is, we assumed `ping` to prove
`pong` and `pong` to prove `ping`. This apparent circularity is broken
by the fact that when proving `ping`, we only assume `pong` has been
correct *in the past*.  When verifying `iso_l`, we show that the
assertion about `ping` is not the first assertion to fail. When
verifying `iso_r`, we show that the assertion about `pong` is not the
first assertion to fail. Since no assertion is the first to fail, we
know no assertion ever fails (this is an argument by [induction](https://en.wikipedia.org/wiki/Mathematical_induction) over time).

# Abstraction

In isolating the left player, IVy deleted all the actions and state
components of the right player. This is a form of abstraction known as
*localization*.  The idea is that the truth of some assertions does not
depend on certain components of the system. But in what cases is this
a sound abstraction? That is, when can we infer that an assertion is true
from the fact that it is true in the abstracted system? A sufficient
condition is that the abstracted actions can have no side effect that
is visible to the remaining actions. We will call this condition
*non-interference*.

IVy uses a fairly simple analysis to check non-interference. As an example,
suppose the right player tries to cheat by putting the ball back in 
the left player's court without hitting it:

    object right_player = {

        ...

        implement intf.ping {
            left_player.ball := true
        }

        ...
    }

Here's what happens when when we try to verify this version:

    $ ivy_check trusted=true interference.ivy 
    Checking isolate iso_l...
    interference.ivy: line 30: error: Call out to right_player.intf_ping[implement] may have visible effect on left_player.ball
    interference.ivy: line 37: referenced here
    interference.ivy: line 20: referenced here
    interference.ivy: line 30: referenced here
    interference.ivy: line 27: referenced here

IVy can't abstract away the right player's implementation of
`intf.ping` because of the possible side effect on `left_player.ball`.
IVy's analysis of interference is based only on which state components
are referenced and assigned. It's easy to construct an example where
two objects share a variable, but do not actually interfere, for
example, because they reference disjoint elements of an array. IVy
will flag this as an error, since its analysis is not precise enough
to show non-interference. IVy is designed to reason about objects that
share interfaces, but not variables.

# Coverage

To be sound, our tactic must also ensure that every assertion in the
program is verified in some isolate. IVy checks this for us. Suppose, for example, we remove this
isolate declaration from our ping-pong program:

    isolate iso_r = right_player with spec

Here is what happens when we try to verify [the program](coveragefail.ivy):

    $ ivy_check trusted=true  coveragefail.ivy
    coveragefail.ivy: line 20: error: assertion is not checked
    coveragefail.ivy: line 5: error: ...in action intf.pong
    coveragefail.ivy: line 49: error: ...when called from right_player.hit
    error: Some assertions are not checked

IVy is telling us that the precondition of action `pong` isn't checked
when it's called from `right_player`, because we haven't created an
isolate for `right_player`.

## The isolate declaration

Now let's look at the `isolate` declaration in more detail. Here is the declaration
that isolates the left player:

    isolate iso_l = left_player with spec

This creates an isolate named `iso_l` in which the guarantees of `left_player` are
checked. The actions of all objects except for `left_player` and
`spec` are abstracted away (assuming they are non-interfering). If we
didn't include `spec` in the `with` part of the declaration, then
`spec` would be abstracted away, and no assertions would be checked
(leading to an error message similar to the one above).

The remaining question is how IVy decides which assertions are
guarantees for `left_player` and which are assumptions. The default
rules are as follows.

A *guarantee* for a given object is any assertion occurring in:

- An implementation provided by the object
- A `before` monitor of an action called by the object
- An `after` monitor of an implementation provided by the object

An *assumption* for a given object is any assertion occurring in:

- A `before` monitor of an implementation provided by the object
- An `after` monitor action called by the object

(`after` specifications will be introduced in the next section).

This roughly corresponds to the intuition that an object makes
assumptions about its inputs and guarantees about its outputs.

## So what have we proved?

If all isolates are correct, and if IVy's non-interference and
coverage checks succeed, then we can infer that all assertions in the
program are true at all times in all executions of the program. In
this case, `ivy_check` prints `OK`. Of course, we only verified the
isolates by randomized testing. This means there is a risk that we
missed a bug in a system component. Because IVy checked our
assume/guarantee proof, however, we know that if the whole system has
a bug, then one of the isolates must have a bug. If we test the
isolates long enough, we will eventually find it without testing the
system as a whole. 

# Layered protocols

We just saw a very simple example of compositional testing of a
peer-to-peer interface. It's also possible to use compositional
testing at the interface between layers in a layered protocol stack.


As an example, let's look at the very simple leader election protocol,
introduced in [this paper](http://dl.acm.org/citation.cfm?id=359108)
in 1979.

In this protocol we have a collection of distributed processes
organized in a ring. Each process can send messages to its right
neighbor in the ring and receive message from left neighbor. A process
has a unique `id` drawn from some totally ordered set (say, the
integers). The purpose of the protocol is to discover which process
has the highest `id` value. This process is elected as the "leader".

This protocol itself is trivially simple. Each process transmits its
own `id` value. When it receives a value, it retransmits the value,
but only if it is *greater than* the process' own `id` value. If a
process receives its own `id`, this value must have traveled all the
way around the ring, so the process knows its `id` is greater than all
others and it declares itself leader.

# Interface specifications

We'll start with a service specification for this protocol:

    object asgn = {

        function pid(X:node.t) : id.t
        axiom [injectivity] pid(X) = pid(Y) -> X = Y
    }

    object serv = {

        action elect(v:node.t)

        object spec = {
            before elect {
                assert asgn.pid(v) >= asgn.pid(X)  
            }
        }
    }

The abstract type `node.t` represents a reference to a process in our
system (for example, its network address). The `asgn` object defines
an assignment of `id` values to nodes, represented by the function
`pid`.  The fact that the `id` values are unique is guaranteed by the
axiom `injectivity`.

The service specification `serv` defines one action `elect` which is
called when a given node is elected leader. Its specification says
that only the node with the maximum `id` value can be elected.

Our protocol consists of a collection of concurrent process layered on
top of two services: a network service and a timer service:

<p><img src="leader_fig1-crop-1.png" alt="Leader Election Ring Figure 1" /></p>

Let's consider now the two intermediate interfaces.  The specification
for the network service is quite simple and comes from IVy's standard
library:

    module ip_simple(addr,pkt) = {

        import action recv(dst:addr,v:pkt)
        export action send(src:addr,dst:addr,v:pkt)

        object spec = {
            relation sent(V:pkt, N:addr)
            after init {
                sent(V, N) := false
            }

            before send {
                sent(v,dst) := true
            }
            before recv {
                assert sent(v,dst)
            }
        }
    }

The interface is a module with two parameters: the type `addr` of
network addresses, and the type `pkt` of packets.  It has two actions,
`recv` and `send`.  The relation `sent` tells us which values have been sent to which
nodes.  Initially, nothing has been sent. The interface provides two
actions `send` and `recv` which are called, respectively, when a value
is sent or received. The `src` and `dst` parameters respectively give the source
and desitination addresses of the packets.

The specification says that a value is marked as sent when `send`
occurs and a value must be marked sent before it can be received.
This describes a network service that can duplicate or re-order
messages, but cannot corrupt messages.

The specification of the timer service is also quite simple and comes
from the standard libarary:

    module timeout_sec = {

        import action timeout

    }

The timer service simply calls `timeout` from time to time, with no
specification as to when.

# Protocol implementation

Now that we have the specificaitons of all the interfaces, let's
define the protocol itself:

    instance net : ip_simple(node.t,id.t)
    instance timer(X:node.t) : timeout_sec

    object proto = {

        implement timer.timeout(me:node.t) = {
            call trans.send(node.next(me),asgn.pid(me))
        }

        implement net.recv(me:node.t,v:id.t) {
            if v = asgn.pid(me) {       # Found a leader!
                call serv.elect(me)
            }
            else if v > asgn.pid(me)  { # pass message to next node
                call trans.send(node.next(me),v)
            }
        }

    }

We create one instance of the network module, and one timer for each
node.  The protocol implements the interface actions `timer.timeout`
and `net.recv`. When a node times out, it transmits the node's `id` to
the next process in the ring, defined by the the action
`node.next` (which we'll define shortly).

When a node receives an id value `v`, it checks whether `v`
is its own id according to the id assignment `asgn`. If so, the
process knows it is leader and calls `serv.elect`. Otherwise, if the
received value is greater, it calls `net.send` to send the value on to
the next node in the ring.


With our protocol implemented, we still need to provide concrete types
for `node` and `id`. If we were formally verifying the protocol, we
would probably treat these as abstract datatypes with specified
mathematical properties. For testing, though, we just need some
concrete types.  Here is one possiblity:

    object node = {
        type t
        interpret t -> bv[1]

        action next(x:t) returns (y:t) = {
            y := x + 1
        }
    }

    object id = {
        type t
        interpret t -> bv[8]
    }

That is, node addresses are one-bit binary numbers (meaning we have just two
nodes, and id's are 8-bit numbers. Often it's a good idea to start testing
with small datatypes. In the case of the leader election ring, more nodes
would increase the amount of time needed to see an election event.

## Compositionally testing the leader election protocol

We're going to divide the system into three isolates, one for each of
its major components. Here is what the three isolates will look like:

<p><img src="leader_fig2-crop-1.png" alt="Leader Election Ring Figure 2" /></p>

Here are the isolate definitions:

    trusted isolate iso_p = proto with serv,node,id,asgn,net,timer
    trusted isolate iso_t = timer
    trusted isolate iso_n = net with node,id

We added the keyword `trusted` to these isolates to indicate to IVy
that they will be verified informally by testing. Notice that the
isolate for `proto` contains its service specification as well as the
specifications of all of the other components. We need to test that
`proto` lives up to its guarantees at all of its interfaces, provided
that all of its assumptions hold. On the other hand, `net` needs only
the specifications of `node` and `id` (the `net` object contains its
own service specification).

We can now use IVy to compile test environments for each of the isolates,
based on the interface specifications. Let's start with the high-level protocol:

    $ ivy_to_cpp isolate=iso_p target=test build=true leader_election_ring.ivy
    g++ -I $Z3DIR/include -L $Z3DIR/lib -g -o leader_election_ring leader_election_ring.cpp -lz3

We run the tester:

    $ ./leader_election_ring
    > timer.timeout(1)
    < net.send(1,0,170)
    > net.recv(0,170)
    < net.send(0,1,170)
    > net.recv(0,170)
    < net.send(0,1,170)
    > net.recv(0,170)
    < net.send(0,1,170)
    > timer.timeout(0)
    < net.send(0,1,149)
    > timer.timeout(0)
    < net.send(0,1,149)
    > timer.timeout(0)
    < net.send(0,1,149)
    > net.recv(0,170)

    ...

    > net.recv(0,170)
    < net.send(0,1,170)
    > timer.timeout(0)
    < net.send(0,1,149)
    > net.recv(1,170)
    < serv.elect(1)

In this run, process 1 times out and sends its id 170 to process
0. Process 0 receives this id and forwards it back to process 1
(meaning process 0's id must be less than 170). Later, process 0 times
out and sends its id 149 to process 1. Eventually, the network decides
to deliver to process 1 the message with its own id, causing process
1 to be elected. When this happens, the assertion monitor checkes that in 
fact process 1 has the highest id.

The important point here is that there is no actual network. The
tester is simulating the network by randomly selecting actions
consistent with the history of actions at the interface. In practice,
this means that the tester stores the relation `sent` (the state of
the network interface specification) and only calls `net.recv` with
packets that have been previously sent. When there are multiple
choices, the tester makes an effort to select uniformly.  This is a
hard problem in general, however. In practice the distribution will be
non-uniform.  If you look at the calls to `net.recv`, you can see that
there is some duplication of sent packets, as we would expect.


We can see here a major advantage of compositional testing over
integration testing. If we used a real network to test our protocol,
we might have to wait a long time for a packet duplication to occur
(in fact, this might never occur unless we take care to stress the
network appropriately). The resilience of our protocol to packet
duplication would not be well tested, as it is here. Similarly, our
protocol might have unintended dependences on timing. Since timeout
events are being generated randomly here, and not based on wall clock
time, we can see timings that might occur rarely in the actual system,
perhaps only under very heavy load.

Now let's turn to the network isolate. We compile and run:

    $ ivy_to_cpp isolate=iso_n target=test build=true leader_election_ring.ivy
    g++ -I $Z3DIR/include -L $Z3DIR/lib -g -o leader_election_ring leader_election_ring.cpp -lz3

    ./leader_election_ring
    > net.send(0,0,168)
    < net.recv(0,168)
    > net.send(0,0,243)
    < net.recv(0,243)
    > net.send(0,0,13)
    < net.recv(0,13)
    > net.send(1,0,108)
    > net.send(0,0,84)
    > net.send(0,0,78)
    < net.recv(0,108)
    < net.recv(0,84)
    < net.recv(0,78)
    > net.send(1,0,17)
    < net.recv(0,17)
    > net.send(0,1,167)
    < net.recv(1,167)
    > net.send(1,0,3)
    > net.send(0,1,13)
    ...

The object `net` is actually just a wrapper around the operating
system's networking API.  Therefore, when we test `net`, we are
actually testing the operating system's networking stack. Fortunately,
testing reveals no errors. Notice though, that the tester is
generating a wider variety of packets than the protocol could
actually generate. In fact, it's simply generating packet values
uniformly at random. In this sense, the network stack is also being
better tested than it would be if composed with the actual protocol.

Finally, we can test the timer:

    $ ivy_to_cpp isolate=iso_t target=test build=true leader_election_ring.ivy
    g++ -I $Z3DIR/include -L $Z3DIR/lib -g -o leader_election_ring leader_election_ring.cpp -lz3

    ./leader_election_ring
    < timer.timeout(0)
    < timer.timeout(1)
    < timer.timeout(0)
    < timer.timeout(1)
    < timer.timeout(0)
    < timer.timeout(1)
    < timer.timeout(0)
    < timer.timeout(1)
    < timer.timeout(0)
    ...

Not very interesting, but it shows both timeouts occurring once every
second, which is what we expect. Again, we are really testing the
operating system here (and also IVy's run time scheduler, which 
uses the operating system API).

# Running the protocol

Now that we've tested the components, we can compile the whole system
and run it as a collection of independent processes. Our protocol is an
example of a [parameterized object](../leader.html). Ivy can decompose it
into a collection of processes based on the parameter `me`.  Each
value of the parameter becomes an individual process. This
transformation is called *parameter stripping*.

To do this, we use the following declaration:

    extract iso_impl(me:node.t) = proto(me),net(me),timer(me),node,id,asgn

This describes a special kind of isolate called an `extract`. Extracts
are intended to be run in production and don't include the
specification monitors. In the extract declaration, `me` is a symbolic
constant that represents the first parameter of of each action and
state component in the object. This parameter is "stripped" by
replacing it with the symbolic constant `me`.

Before thinking about this too hard, let's just run it to see what
happens. We compile as usual, with one difference: we use the option
`target=repl`.  Instead of generating a test environment, IVy provides
a read-eval-print loop as the environment:

    $ ivy_to_cpp target=repl isolate=iso_impl build=true leader_election_ring.ivy
    g++ -I $Z3DIR/include -L $Z3DIR/lib -g -o leader_election_ring leader_election_ring.cpp -lz3

This produces an executable that takes one parameter `me` on the
command line. Let's create two terminals A and B to run process 0 and
process 1 respectively:

    A: $ ./leader_election_ring 0
    A: >

    B: $ ./leader_election_ring 1
    B: >

    A: < serve.elect
    A: < serve.elect
    A: < serve.elect
    ...

Notice that nothing happens when we start node 0. It is sending packets
once per second, but they are being dropped because no port is yet
open to receive them. After we start node 1, it forwards node 0's
packets, which causes node 0 to be elected (and to continues to be
elected once per second).
