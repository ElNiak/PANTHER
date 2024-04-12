---
layout: page
title: "Deduction example: majority"
---

In consensus protocols such as Paxos and Raft, we typically need a
datatype representing a subset of some finite set (the *basis* set)
and we need to test whether subset contains a majority of the basis
elements.

The key fact we need to know about majorities is that two majorities
always have an alement in common. We will call this the majority
intersection property. Here, we will develop an abstract datatype
for subsets of a finite basis set provided with the operations for
building subsets and a computable majority prediate satisfying the
the majority intersection property.

Our datatype takes a type *basis* as a parameter. This must be a
sequence type equipped with a value `max` representing the maximum
value of the sequence.  Sequence types provide a total order, a zero
element, schemata for induction and recursion, and an arithmetic
theory.

The module provides the following interface:

1) a type *this* representing subsets of the basis type in the range [0,max-1]
2) a *member* relation
3) a predicate `majority` on sets that is true if the cardinality is > n/2.
4) an action `empty` returning the empty set
5) an action `add` that adds an element to a set
6) an action `is_empty` returning true if a set is empty

Internally, the following are also used:

1) An unbounded sequence type `index` used for counting elements of `basis`
2) a relation *disjoint* beteween sets
3) a function *card* giving the cardinality of a set as an index
5) a function *cnt* gives the cardinality of the set of the set [0,x]

The index type is needed in order to represent the cardinality of
the set `[0,max]`, which is `max+1` and thus cannot be represented
by `basis`.

Note the functions above are stratified in this order: `set -> basis
-> index.t`.

The implementation gives computable definitions of card, cnt and majority.
The complexity of card and majority is quadratic in n, which is not optimimal
but should be acceptable for small n (say, up to 5). In principal, we could
add more efficient actions that compute these functions.

The main property provided is that any two majorities have an
element in common.  To prove this, we use a lemma stating that the
sum of the cardinalities of two disjoint sets is <= cnt(n-1). This
is proved by induction on n. This lemma implies the majority
property.


```
include collections
include order
include deduction

```
The parameters of the module are:

 - basis: the basis object (instance of unbounded_sequence)
 - index: the index object (instance of unbounded_sequence)


```
module indexset(basis) = {

    type set 
    instance index : unbounded_sequence

    relation member(E:basis,S:set)
    function card(S:set) : index.t
    relation majority(S:set)

    action empty returns(s:set)
    action add(s:set,e:basis) returns (s:set)
    action is_empty(s:set) returns(r:bool)

    object spec = {

	after empty {
	    assert ~member(E,s);
	}

	after add {
	    assert member(X,s) <-> (member(X,old s) | X = e)
	}

	after is_empty {
	    assert r <-> ~ exists X. member(X,s)
	}
    }

    function cnt(E:basis) : index.t
    relation disjoint(X:set,Y:set)


    isolate disjointness = {

	object impl = {
```
The funtion cnt(x) returns the cardinality of the set of
ordinals < x. We define it recursively by instantiating
the recursion scheman fo the basis type.

Note here we use a definition schema. A definition of the form
`f(x:t) = ...` is a shorthand for this schema:

    # {
    #     individual x :t
    #     #----------------
    #     property f(x) = ...
    # }

The `auto` tactic will only unfold this definition
schema for ground terms *x* occurring in the proof
goal. Without this, we would exit the decidable
fragment, due to a quantified variable under an
arithmetic operator in the following definition.

```
	    definition cnt(x:basis) = 1 if x <= 0 else cnt(x-1) + 1
	    proof
                apply rec[basis]

```
We define cardinality in terms of a recursive function
cardUpTo that counts the number of elements in a set
that are less than or equal to a bound B.

```
	    function cardUpTo(S:set,B:basis) : index.t

```
Note that again the we use definition schema to stay
decidable. Again, the `rec[t]` schema is used to admit a
recursive definition.

```
	    definition cardUpTo(s:set,b:basis) =
		(1 if member(b,s) else 0) if b <= 0
                else (cardUpTo(s,b-1) + (1 if member(b,s) else 0))
	    proof
               apply rec[basis]

```
The cardinality function is then defined in terms of cardUpTo.

```
	    definition card(S) = cardUpTo(S,basis.max)

```
A majority is a set whose cardinality is greater than 1/2 of
the basis set.

```
	    definition majority(X) = 2 * card(X) > cnt(basis.max)

	    object spec = {
```
This is the definition of dijoint sets in terms of
the member relation.  Notice that there is a
quantifier alternation in the direction set ->
basis.

```
		definition 
                    disjoint(X,Y) = forall E. ~(member(E,X) & member(E,Y))

```
This is our inductive invariant. It says that, for
disjoint sets, the sum of the cardinalities up to
bound B is less than the total number of elements
less than B. We prove it by induction on B, using
the induction schema for type `basis`. As usual,
we have to giev the induction parameter explicitly,
since Ivy can't infer it automatically.

Most importantly, notice how arithmetic is used
here. Because we used definition schemata, we never
have an arithmetic applied to a universally
quantified variable. This means our verification condition
is is in the essentially uninterpreted fragment.

```
		property disjoint(X,Y) -> cardUpTo(X,B) + cardUpTo(Y,B) <= cnt(B)
		proof
                    apply ind[basis] with X = B;
                    showgoals
	    }

	}

	object spec = {

```
With the above lemma, Z3 can prove the "majorities intersect"
property. The idea is that the lemma can be specialized to this:

     # property disjoint(X,Y) -> card(X) + card(Y) <= cnt(basis.max)

Since both majorities have cardinality greater than
`cnt(basis.max)/2`, it follows that majorities cannot be
disjoint, so they must have an element in common.

```
            property majority(X) & majority(Y) -> exists E. (member(E,X) & member(E,Y))
	}

	attribute test = impl
    }
    with basis.impl,index.impl

```
Note: we use the *implementations* of the basis and index
types. That means both are interpreted. Fortunately, we don't
run afoul of the fragment checker.

```
    isolate api = {

	object impl = {
```
Here is the implementation of the set type using an unsorted array.

```
	    instance arridx : unbounded_sequence
	    instance arr:array(arridx,basis)

```
Tricky: this is a bit of aspect-orientation. It turns the type `set` into a struct
with just one field called `repr`. This field gives the concrete representation of a
set as an array. To an isolate that doesn't use the definition of `member` below,
the tpye `set` will still appear to be uninterpreted.

```
	    destructor repr(X:set) : arr.t

	    definition member(y:basis,X:set) = exists Z. 0 <= Z & Z < repr(X).end & repr(X).value(Z) = y

```
These lemmas are needed to prove correctness of is_empty. 

```
	    property member(Y,X) -> repr(X).end ~= 0
	    property repr(X).end ~= 0 -> member(repr(X).value(0),X)

	    implement empty {
		repr(s) := arr.create(0,0)
	    }

	    implement add {
		if ~member(e,s) {
		    repr(s) := arr.resize(repr(s),repr(s).end.next,e)
		}
	    }

	    implement is_empty {
		r := repr(s).end = 0;
	    }
	}

	attribute test = impl

    } with spec

    attribute test = impl
}


```

The following is a test instantiation of `indexset`, to check that the
verification goes through.


```
instance basis : unbounded_sequence
object basis = { ...
    var max : basis
}

instance nset : indexset(basis)

export nset.empty
export nset.add
export nset.is_empty
```
