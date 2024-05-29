#
# Copyright (c) Microsoft Corporation. All Rights Reserved.
#

import ivy_utils as iu
import ivy_logic as il
import ivy_logic_utils as lu
import ivy_ast as ia
import logic_util

class Redefinition(iu.IvyError):
    pass
class Circular(iu.IvyError):
    pass
class NoMatch(iu.IvyError):
    pass
class ProofError(iu.IvyError):
    pass
class CaptureError(iu.IvyError):
    pass



class MatchProblem(object):
    def __init__(self,schema,pat,inst,freesyms,constants,prem_matches=[]):
        self.schema,self.pat,self.inst,self.freesyms,self.constants = schema,pat,inst,set(freesyms),constants
        self.prem_matches=prem_matches
        self.revmap = dict()
    def __str__(self):
        return '{{pat:{},inst:{},freesyms:{}}}'.format(self.pat,self.inst,map(str,self.freesyms))

def attrib_goals(proof,goals):
    if hasattr(proof,'lineno'):
        for g in goals:
            g.lineno = proof.lineno
    return goals

class ProofChecker(object):
    """ This is IVY's built-in proof checker """

    def __init__(self,axioms,definitions,schemata=None):
        """ A proof checker starts with sets of axioms, definitions and schemata
    
        - axioms is a list of ivy_ast.LabeledFormula
        - definitions is a list of ivy_ast.LabeledFormula
        - schemata is a map from string names to ivy_ast.LabeledFormula

        The schemata argument is optional and is included for backward compatibility
        with ivy_mc.
        """
    
        self.axioms  = [normalize_goal(ax) for ax in axioms]
        self.definitions = dict((d.formula.defines().name,normalize_goal(d)) for d in definitions)
        self.schemata = dict((x,normalize_goal(y)) for x,y in schemata.iteritems()) if schemata is not None else dict()
        for ax in axioms:
            if ax.label is not None:
                self.schemata[ax.name] = ax
        self.stale = set() # set of symbols that are not fresh
        for lf in axioms + definitions:
            self.stale.update(lu.used_symbols_ast(lf.formula))
        for goal in schemata.values():
            vocab = goal_vocab(goal)
            self.stale.update(vocab.symbols)

    def admit_axiom(self,ax):
        self.axioms.append(normalize_goal(ax))
        if ax.label is not None:
            self.schemata[ax.name] = ax

    def admit_definition(self,defn,proof=None):
        """ Admits a definition if it is non-recursive or match a definition schema. 
            If a proof is given it is used to match the definition to a schema, else
            default heuristic matching is used.
        
        - defn is an ivy_ast.LabeledFormula
        """

        defn = normalize_goal(defn)
        sym = defn.formula.defines()
        if sym.name in self.definitions:
            raise Redefinition(defn,"redefinition of {}".format(sym))
        if sym in self.stale:
            raise Circular(defn,"symbol {} defined after reference".format(sym))
        deps = list(lu.symbols_ast(defn.formula.rhs()))
        self.stale.update(deps)
        if sym in deps:
            # Recursive definitions must match a schema
            if proof is None:
                raise NoMatch(defn,"no proof given for recursive definition")
            subgoals = self.apply_proof([defn],proof)
            if subgoals is None:
                raise NoMatch(defn,"recursive definition does not match the given schema")
        else:
            subgoals = []
        self.definitions[sym.name] = defn
        return subgoals
        
    def admit_proposition(self,prop,proof=None,subgoals=None):
        """ Admits a proposition with proof.  If a proof is given it
            is used to match the definition to a schema, else default
            heuristic matching is used. If a list of subgoals is supplied, it is
            assumed that these entail prop and the proof is applied to
            the subgoals.
        
        - prop is an ivy_ast.LabeledFormula
        """

        prop = normalize_goal(prop)
        if isinstance(prop.formula,il.Definition):
            return self.admit_definition(prop,proof)
        if proof is None:
            raise NoMatch(prop,"no proof given for property")
        subgoals = subgoals or [prop]
        subgoals = self.apply_proof(subgoals,proof)
        if subgoals is None:
            raise NoMatch(proof,"goal does not match the given schema")
        self.axioms.append(prop)
        self.schemata[prop.name] = prop
        vocab = goal_vocab(prop)
        self.stale.update(vocab.symbols)
        return subgoals

    def get_subgoals(self,prop,proof):
        """Return the subgoals that result from applying proof to property
            prop, but do not admit prop in the context. Note, prop may not
            be a definition.

        """
        assert not isinstance(prop.formula,il.Definition)
        prop = normalize_goal(prop)
        subgoals = self.apply_proof([prop],proof)
        if subgoals is None:
            raise NoMatch(proof,"goal does not match the given schema")
        return subgoals
        

    def apply_proof(self,decls,proof):
        """ Apply a proof to a list of goals, producing subgoals, or None if
        the proof fails. """

        with ia.ASTContext(proof):
            if len(decls) == 0:
                return []
            if isinstance(proof,ia.SchemaInstantiation):
                m = self.match_schema(decls[0],proof)
                return None if m is None else m + decls[1:]
            elif isinstance(proof,ia.LetTactic):
                return self.let_tactic(decls,proof)
            elif isinstance(proof,ia.ComposeTactics):
                return self.compose_proofs(decls,proof.args)
            elif isinstance(proof,ia.AssumeTactic):
                return self.assume_tactic(decls,proof)
            elif isinstance(proof,ia.UnfoldTactic):
                return self.unfold_tactic(decls,proof)
            elif isinstance(proof,ia.ForgetTactic):
                return self.forget_tactic(decls,proof)
            elif isinstance(proof,ia.ShowGoalsTactic):
                return self.show_goals_tactic(decls,proof)
            elif isinstance(proof,ia.DeferGoalTactic):
                return self.defer_goal_tactic(decls,proof)
            elif isinstance(proof,ia.DeferGoalTactic):
                return self.defer_goal_tactic(decls,proof)
            elif isinstance(proof,ia.LetTactic):
                return self.let_tactic(decls,proof)
            elif isinstance(proof,ia.IfTactic):
                return self.if_tactic(decls,proof)
            elif isinstance(proof,ia.NullTactic):
                return decls
            elif isinstance(proof,ia.PropertyTactic):
                return self.property_tactic(decls,proof)
            elif isinstance(proof,ia.FunctionTactic):
                return self.function_tactic(decls,proof)
            elif isinstance(proof,ia.TacticTactic):
                return self.tactic_tactic(decls,proof)
            elif isinstance(proof,ia.ProofTactic):
                return self.proof_tactic(decls,proof)
            elif isinstance(proof,ia.WitnessTactic):
                return self.witness_tactic(decls,proof)
            assert False,"unknown proof type {}".format(type(proof))

    def proof_tactic(self,decls,proof):
        for idx,decl in enumerate(decls):
            if decl.label.rep == proof.label.rep:
                return decls[:idx] + decls[idx+1:] + self.apply_proof([decl],proof.proof)
        raise iu.IvyError(proof,'no goal with label {}'.format(proof.label))

    def tactic_tactic(self,decls,proof):
        tn = proof.tactic_name
        if tn not in registered_tactics:
            raise iu.IvyError(proof,'unknown tactic: {}'.format(tn))
        tactic = registered_tactics[tn]
        return tactic(self,decls,proof)
    
    def compose_proofs(self,decls,proofs):
        for proof in proofs:
            decls = self.apply_proof(decls,proof)
            if decls is None:
                return None
        return decls

    def show_goals_tactic(self,decls,proof):
        print
        print '{}Proof goals:'.format(proof.lineno)
        for decl in decls:
            print
            print 'theorem ' + str(decl)
            print
        return decls

    def defer_goal_tactic(self,decls,proof):
        return decls[1:] + decls[0:1]

    def let_tactic(self,decls,proof):
        goal = decls[0]
        vocab = goal_vocab(goal)
        defs = [compile_expr_vocab(ia.Atom('=',x.args[0],x.args[1]),vocab) for x in proof.args]
        cond = il.And(*[il.Equals(a.args[0],a.args[1]) for a in defs])
        subgoal = ia.LabeledFormula(decls[0].label,il.Implies(cond,decls[0].formula))
        if not hasattr(decls[0],'lineno'):
            print 'has no line number: {}'.format(decls[0])
            exit(1)
        subgoal.lineno = decls[0].lineno
        return attrib_goals(proof,[subgoal]) + decls[1:]

    def property_tactic(self,decls,proof):
        goal = decls[0]
        vocab = goal_vocab(goal)
        cut = compile_expr_vocab(proof.args[0],vocab)
        cut = normalize_goal(cut)
        subgoal = goal_subst(goal,cut,cut.lineno)
        lhs = proof.args[1]
        if not isinstance(lhs,ia.NoneAST):
            fmla = il.drop_universals(cut.formula)
            if not il.is_exists(fmla) or len(fmla.variables) != 1:
                raise IvyError(proof,'property is not existential')
            evar = list(fmla.variables)[0]
            rng = evar.sort
            vmap = dict((x.name,x) for x in lu.variables_ast(fmla))
            used = set()
            args = lhs.args
            targs = []
            for a in args:
                if a.name in used:
                    raise IvyError(lhs,'repeat parameter: {}'.format(a.name))
                used.add(a.name)
                if a.name in vmap:
                    v = vmap[a.name]
                    targs.append(v)
                    if not (il.is_topsort(a.sort) or a.sort != v.sort):
                        raise IvyError(lhs,'bad sort for {}'.format(a.name))
                else:
                    if il.is_topsort(a.sort):
                        raise IvyError(lhs,'cannot infer sort for {}'.format(a.name))
                    targs.append(a)
            for x in vmap:
                if x not in used:
                    raise IvyError(lhs,'{} must be a parameter of {}'.format(x,lhs.rep))
            dom = [x.sort for x in targs]
            sym = il.Symbol(lhs.rep,il.FuncConstSort(*(dom+[rng])))
            if sym in self.stale or sym in goal_defns(goal):
                raise iu.IvyError(lhs,'{} is not fresh'.format(sym))
            term = sym(*targs) if targs else sym
            fmla = lu.substitute_ast(fmla.body,{evar.name:term})
            cut = clone_goal(cut,[],fmla)
            goal = goal_add_prem(goal,ia.ConstantDecl(sym),goal.lineno)
        
        subgoals = [subgoal]
        pf = proof.args[2]
        if not isinstance(pf,ia.NoneAST):
            subgoals = self.apply_proof(subgoals,pf)
            if subgoals is None:
                return None
        return [goal_add_prem(goal,cut,cut.lineno)] + decls[1:] + subgoals

    def function_tactic(self,decls,proof):
        goal = decls[0]
        vocab = goal_vocab(goal)
        free = goal_free(goal)
        for df in proof.args:
            if isinstance(df,ia.ConstantDecl):
                assert False
            else:
                lf = df.args[0]
                lhs = lf.formula.args[0]
                ts = il.TopFunctionSort(len(lhs.args))
                newsym = il.Symbol(lhs.rep,ts)
                with il.WithSymbols([newsym]):
                    vars = lf.formula.args[0].args
                    fmla = ia.Forall(vars,ia.Atom('=',lf.formula.args))
                    elf = lf.clone([lf.label,fmla])
                    lf = compile_expr_vocab(elf,vocab)
                sym = lf.formula.body.args[0].rep
                deps = list(lu.symbols_ast(lf.formula.body.args[1]))
                if sym in deps:
                    raise NoMatch(lf,"no proof given for recursive definition")
                # TODO: allow proofs of recursive definitions
                cd = ia.ConstantDecl(sym)
                cd.lineno = lf.lineno
                lf.definition = True
                goal = goal_add_prem(goal,cd,lf.lineno)
                goal = goal_add_prem(goal,lf,lf.lineno)
            if sym in vocab.sorts or sym in vocab.symbols or sym in free:
                raise Redefinition(df,"redefinition of {}".format(sym))
        return [goal] + decls[1:]

    def lookup_schema(self,schemaname,decl,ast,close=False):
        if schemaname in self.schemata:
            schema = self.schemata[schemaname]
            check_schema_capture(schema,decl)
        elif schemaname in self.definitions:
            schema = self.definitions[schemaname]
            fmla = goal_conc(schema).to_constraint()
            fmla = il.close_formula(fmla) if close else fmla
            schema = clone_goal(schema,goal_prems(schema),fmla)
            check_schema_capture(schema,decl)
        else:
            premmap = dict((x.name,x) for x in goal_prem_goals(decl))
            if schemaname in premmap:
                schema = premmap[schemaname]
            else:
                raise ProofError(ast,"No property {} exists in the current context".format(schemaname))
        return schema
    
    def setup_matching(self,decl,proof,allow_witness=False):
        schemaname = proof.schemaname()
        schema = self.lookup_schema(schemaname,decl,proof)
        return self.setup_schema_matching(decl,proof,schema,allow_witness=allow_witness)
        
    def setup_schema_matching(self,decl,proof,schema,allow_witness=False):
        schema = rename_goal(schema,proof.renaming())
        schema = transform_defn_schema(schema,decl)
        prob = match_problem(schema,decl)
        prob = transform_defn_match(prob)
        if prob is None:
            raise NoMatch(proof,'definition does not match the given schema')
        proof_match,prob = add_prem_match(proof.match(),prob,decl,self)
        pmatch = compile_match(proof_match,prob,decl,allow_witness)
        if pmatch is None:
            raise ProofError(proof,'Match is inconsistent')
        return prob, pmatch

    def assume_tactic(self,decls,proof):
        decl = decls[0]
        schemaname = proof.schemaname()
        premmap = dict((x.name,x) for x in goal_prem_goals(decl))
        if schemaname in premmap:
            schema = premmap[schemaname]
            if isinstance(proof.label,ia.NoneAST):
                decl = goal_remove_prem(decl,schemaname)
        else:
            schema = self.lookup_schema(schemaname,decl,proof,close=False)
        schema = remove_explicit(schema)
        prob, pmatch = self.setup_schema_matching(decl,proof,schema,allow_witness=True)
        def iswit(x):
            return isinstance(x,il.Variable) and x not in prob.freesyms
        witness = dict((x,y) for x,y in pmatch.iteritems() if iswit(x))
        pmatch = dict((x,y) for x,y in pmatch.iteritems() if not iswit(x))
#        prem = make_goal(proof.lineno,fresh_label(goal_prems(decl)),[],schema)
        prem = prob.schema
        if schemaname not in premmap:
            prem = close_unmatched(prem,pmatch)
        conc = goal_conc(prem)
        conc = lu.witness_ast(True,[],witness,conc)
        prem = clone_goal(prem,goal_prems(prem),conc)
        prem  = apply_match_goal(pmatch,prem,apply_match_alt)
        prem = drop_supplied_prems(prem,decl,proof.match())
        if not isinstance(proof.label,ia.NoneAST):
            prem = prem.clone([proof.label,prem.formula])
        if any(prem.name == x.name for x in goal_prem_goals(decl)):
            raise ProofError(proof,'instance name {} clashes with context'.format(prem.name))
        return [goal_add_prem(decl,prem,proof.lineno)] + decls[1:]

    def unfold_tactic(self,decls,proof):
        decl = decls[0]
        defns = []
        for unfspec in proof.unfspecs:
            defname = unfspec.defname
            defn = self.lookup_schema(defname,decl,proof)
            rdefs = [rename_goal(defn,rn) for rn in unfspec.renamings]
            rdefs.append(defn)
            defns.append(rdefs)
        if proof.has_premise:
            premname = proof.premname
            decl = goal_apply_to_prem(decl,premname,lambda goal: unfold_goal(goal,defns))
            if decl is None:
                raise ProofError(proof,'no premise {} found to unfold in'.format(premname))
        else:
            decl = goal_apply_to_conc(decl,lambda fmla: unfold_fmla(fmla,defns))
        return [decl] + decls[1:]

    def forget_tactic(self,decls,proof):
        decl = decls[0]
        prems = goal_prems(decl)
        prems = [p for p in prems if not (isinstance(p,ia.LabeledFormula)
                                          and p.name in proof.premnames)]
        decl = clone_goal(decl,prems,goal_conc(decl))
        return [decl] + decls[1:]

    def if_tactic(self,decls,proof):
        cond = proof.args[0]
        true_goal = ia.LabeledFormula(decls[0].label,il.Implies(cond,decls[0].formula))
        true_goal.lineno = decls[0].lineno
        false_goal = ia.LabeledFormula(decls[0].label,il.Implies(il.Not(cond),decls[0].formula))
        false_goal.lineno = decls[0].lineno
        return (attrib_goals(proof.args[1],self.apply_proof([true_goal],proof.args[1])) +
                attrib_goals(proof.args[2],self.apply_proof([false_goal],proof.args[2])) +
                decls[1:])

    def match_schema(self,decl,proof):
        """ attempt to match a definition or property decl to a schema

        - decl is an ivy_ast.Definition or ivy_ast.Property
        - proof is an ivy_ast.SchemaInstantiation

        Returns a match or None
        """

        if isinstance(goal_conc(decl),ia.TemporalModels):
            raise NoMatch(proof,"goal does not match the given schema")
        prob, pmatch = self.setup_matching(decl,proof)
        apply_match_to_problem(pmatch,prob,apply_match_alt)
        if isinstance(prob.pat,ia.Tuple):
            for idx in range(len(prob.pat.args)):
                fomatch = fo_match(prob.pat.args[idx],prob.inst.args[idx],prob.freesyms,prob.constants)
                if fomatch is not None:
                    apply_match_to_problem(fomatch,prob,apply_match)
                somatch = match(prob.pat.args[idx],prob.inst.args[idx],prob.freesyms,prob.constants)
                if somatch is None:
                    raise NoMatch(proof,"goal does not match the given schema")
                apply_match_to_problem(somatch,prob,apply_match_alt)
        else:
            fomatch = fo_match(prob.pat,prob.inst,prob.freesyms,prob.constants)
            if fomatch is not None:
                apply_match_to_problem(fomatch,prob,apply_match)
            somatch = match(prob.pat,prob.inst,prob.freesyms,prob.constants)
            if somatch is None:
                raise NoMatch(proof,"goal does not match the given schema")
            apply_match_to_problem(somatch,prob,apply_match_alt)
        detect_nonce_symbols(prob)
#            schema = apply_match_goal(pmatch,schema,apply_match_alt)
#            schema = apply_match_goal(fomatch,schema,apply_match)
#            schema = apply_match_goal(somatch,schema,apply_match_alt)
            # tmatch = apply_match_match(fomatch,pmatch,apply_match)
            # tmatch = apply_match_match(somatch,tmatch,apply_match_alt)
            # schema = apply_match_goal(tmatch,schema,apply_match_alt)
        return goal_subgoals(prob.schema,decl,proof.lineno)

    def witness_tactic(self,decls,proof):
        wits = compile_witness_list(proof,decls[0])
        for wit in wits:
            if not il.is_variable(wit.args[0]):
                raise iu.IvyError(wit,'left-hand side of witness must be a variable')
        wit_map = dict((x.args[0],x.args[1]) for x in wits)
        decl = decls[0]
        conc = goal_conc(decl)
        conc = lu.witness_ast(False,[],wit_map,conc)
        prems = goal_prems(decl)
        return [clone_goal(decl,prems,conc)] + decls[1:]
 

# A proof goal is a LabeledFormula whose body is either a Formula or a SchemaBody

# Get the conclusion of a goal

def goal_conc(g):
    return g.formula.conc() if isinstance(g.formula,ia.SchemaBody) else g.formula

# Get the premises of a goal

def goal_prems(g):
    return list(g.formula.prems()) if isinstance(g.formula,ia.SchemaBody) else []

# Make a goal with given label, premises (goals), conclusion (formula)

def make_goal(lineno,label,prems,conc,annot=None):
    if isinstance(label,str):
        label = ia.Atom(label)
    res =  ia.LabeledFormula(label,ia.SchemaBody(*(prems+[conc])) if prems else conc)
    res.lineno = lineno
    if annot is not None:
        res.annot = annot
    return res

# Replace the premises and conclusions of a goal, keeping label and lineno
def clone_goal(goal,prems,conc):
    return goal.clone_with_fresh_id([goal.label,ia.SchemaBody(*(prems+[conc])) if prems else conc])

# Substitute a goal g2 for the conclusion of goal g1. The result has the label of g2.

def goal_subst(g1,g2,lineno):
    check_name_clash(g1,g2)
    return make_goal(lineno, g2.label, goal_prems(g1) + goal_prems(g2), goal_conc(g2))

# Substitute a sequence of subgoals in to the conclusion of the first goal

def goals_subst(goals,subgoals,lineno):
    return [goal_subst(goals[0],g,lineno) for g in subgoals] + goals[1:]

# Add a formula or schema as a premise to a goal. Make up a fresh name for it.

# Make a fresh label not used in any of a list of goals

def fresh_label(goals):
    rn = iu.UniqueRenamer(used=[x.name for x in goals])
    return ia.Atom(rn(),[])
    
# Add a premise to a goal

def goal_add_prem(goal,prem,lineno):
    return make_goal(lineno,goal.label,goal_prems(goal) + [prem], goal_conc(goal))
    

def goal_remove_prem(goal,prem_name):
    goal = clone_goal(goal,[x for x in goal_prems(goal) if x.name != prem_name],goal_conc(goal))
    return goal

# Add a premise to a goal

def goal_prefix_prems(goal,prems,lineno):
    return make_goal(lineno,goal.label,prems + goal_prems(goal), goal_conc(goal))

# Get the symbols and types defined in the premises of a goal

def goal_defns(goal):
    res = set()
    for x in goal_prems(goal):
        if isinstance(x,ia.ConstantDecl) and isinstance(x.args[0],il.Symbol):
            res.add(x.args[0])
        elif isinstance(x,il.UninterpretedSort):
            res.add(x)
    return res

# Get all the premises of a goal that are goals

def goal_prem_goals(goal):
    return [x for x in goal_prems(goal) if isinstance(x,ia.LabeledFormula)]

# Check that there are no name clashes in a pair of goals

def check_name_clash(g1,g2):
    d1,d2 = map(goal_defns,(g1,g2))
    for s1 in d1:
        if s1 in d2:
            raise ProofError(None,'premise {} of sugboal clashes with context'.format(s1))

# A *vocabulary* consists of three lists: sorts, symbols and variables

class Vocab(object):
    def __init__(self,sorts,symbols,variables):
        self.sorts,self.symbols,self.variables = sorts,symbols,variables

# Get the vocabulary of a goal. This is the collection of sorts, symbols and
# variables that are bound in the goal.

def goal_vocab(goal):
    prems = goal_prems(goal)
    conc = goal_conc(goal)
    symbols = [x.args[0] for x in prems if isinstance(x,ia.ConstantDecl)]
    sorts = [s for s in prems if isinstance(s,il.UninterpretedSort)]
    fmlas = [x.formula for x in prems if isinstance(x,ia.LabeledFormula)] + [conc]
    variables = list(lu.used_variables_asts(fmlas))
    return Vocab(sorts,symbols,variables)

# Check that the conclusions of two goals match

def check_concs_match(g1,g2):
    c1,c2 = map(goal_conc,(g1,g2))
    if not il.equal_mod_alpha(c1,c2):
        raise ProofError(None,'conclusions do not match:\n    {}\n     {}'.format(c1,c2))

# Check that the non-proposition premises of g1 are provided by g2.

def check_premises_provided(g1,g2):
    defns = goal_defns(g2)
    for thing in goal_defns(g1):
#        syms = lu.used_symbols_ast(thing) if il.is_lambda(thing) else [thing]
        syms = [] if il.is_lambda(thing) else [thing]
        for sym in syms:
            if sym not in defns and not il.sig.contains(sym):
                raise ProofError(None,'premise "{}" does not match anything in the environment'.format(thing))

def goal_is_defn(x):
    if isinstance(x,ia.ConstantDecl):
        return not il.is_lambda(x.args[0])
    return isinstance(x,il.UninterpretedSort)

def goal_defines(x):
    if isinstance(x,ia.ConstantDecl):
        return x.args[0]
    return x

def normalize_goal(x):
    """ normalize the subformulas of a goal, so there are only binary
    conjunctions/disjunctions and single-variable quantifiers. """
    if goal_is_defn(x):
        return x
    if not hasattr(x,'formula'):
        print x
        print type(x)
    return clone_goal(x,map(normalize_goal,goal_prems(x)),il.normalize_ops(goal_conc(x)))

def get_unprovided_defns(g1,g2):
    defns = goal_defns(g2)
    res = []
    for prem in goal_prems(g1):
        if goal_is_defn(prem):
            sym = goal_defines(prem)
            if sym not in defns and not il.sig.contains(sym):
                res.append(prem)
    return res

# Turn the propositional premises of a goal into a list of subgoals. The
# symbols and types in the goal must be provided by the environment.

def goal_subgoals(schema,goal,lineno):
    check_concs_match(schema,goal)
    upds = get_unprovided_defns(schema,goal)
    g = clone_goal(goal,upds,goal_conc(goal))
    goal = goal_subst(goal,g,lineno)
    gpms = goal_prem_goals(goal)
    subgoals = [goal_subst(goal,x,lineno) for x in goal_prem_goals(schema)
                if not any(goals_eq_mod_alpha(x,y) for y in gpms)]
    subgoals = [s for s in subgoals if not trivial_goal(s)]
    return subgoals

def fmla_vocab(fmla):
    """ Get the free vocabulary of a formula, including sorts, symbols and variables """
    
    things = lu.used_sorts_ast(fmla)
    things.update(lu.used_symbols_ast(fmla))
    things.update(lu.used_variables_ast(fmla))
    return things


def goal_free(goal):
    """ Get the free vocabulary of a goal, including sorts, symbols and variables """
    bound = set()
    def rec_fmla(fmla,res):
        for y in fmla_vocab(fmla):
            if y not in bound:
                res.add(y)
    def rec(goal,res):
        defns = goal_defns(goal)
        with il.BindSymbols(bound,defns):
            for x in goal_prem_goals(goal):
                if isinstance(x.formula,ia.SchemaBody):
                    rec(x,res)
                else:
                    rec_fmla(x.formula,res)
            rec_fmla(goal_conc(goal),res)
    res = set()
    rec(goal,res)
    return res

# Make sure the free vocabulry of the schema we are about to use is not captured
# by bindings in the goal. 

def check_schema_capture(schema,goal):
    gvocab = goal_vocab(goal)
    fvocab = goal_free(schema)
    for sym in fvocab:
        if sym in gvocab.sorts or sym in gvocab.symbols:
            raise CaptureError(None,'"{}" is captured when importing "{}"'.format(sym,schema.name))

def check_alpha_capture(goal,match):
    rev_match = dict((y,x) for x,y in match.iteritems())
    for s in goal_free(goal).union(goal_defns(goal)):
        if s in rev_match and s not in match:
            raise CaptureError(None,'"{}" is captured by renaming "{}"'.format(s,rev_match[s]))

def check_renaming(goal,renaming):
    fwd = dict()
    rev = dict()
    for x in renaming.args:
        l,r = x.lhs().rep, x.rhs().rep
        if l in fwd:
            raise ProofError(None,'"{}" is renamed to both "{}" and "{}"'.format(l,fwd[l],r))
        if r in rev:
            raise ProofError(None,'both "{}" and "{}" are renamed to "{}"'.format(rev[r],l,r))
        fwd[l] = r
        fwd[r] = l
    return
        
def rename_goal(goal,renaming):
    if len(renaming.args) == 0:
        return goal
    check_renaming(goal,renaming)
    rmap = dict((x.lhs().rep,x.rhs().rep) for x in renaming.args)
    def rec_goal(goal):
        if not isinstance(goal,ia.LabeledFormula):
            return goal
        goal = clone_goal(goal,map(rec_goal,goal_prems(goal)),goal_conc(goal))
        match = dict((x,x.rename(lambda n: rmap[x.name])) for x in goal_defns(goal) if x.name in rmap)
        match = dict((x,apply_match_sym(match,y)) for x,y in match.iteritems())
        check_alpha_capture(goal,match)
        goal = apply_match_goal(match,goal,apply_match_alt)
        goal = clone_goal(goal,goal_prems(goal),il.alpha_rename(rmap,goal_conc(goal)))
        goal = goal.rename(rmap.get(goal.name,goal.name))
        return goal
    res = rec_goal(goal)
    return res
                
            
            

# Compile an expression using a vocabulary. The expression could be a formula or a type.

def compile_expr_vocab(expr,vocab):
    with il.WithSymbols(vocab.symbols):
        with il.WithSorts(vocab.sorts):
            if isinstance(expr,ia.Atom) and expr.rep in il.sig.sorts:
                return il.sig.sorts[expr.rep]
            with il.top_sort_as_default():
                with ia.ASTContext(expr):
                    expr = il.sort_infer_list([expr.compile()] + vocab.variables)[0]
                    return expr


# Compile an expression using a vocabulary. The expression could be a formula or a type.

def compile_expr_vocab_ext(expr,vocab):
    with il.WithSymbols(vocab.symbols):
        with il.WithSorts(vocab.sorts):
            if isinstance(expr,ia.Atom) and expr.rep in il.sig.sorts:
                return il.sig.sorts[expr.rep]
            with il.top_sort_as_default():
                with ia.ASTContext(expr):
                    expr = expr.compile()
                    return expr


def remove_vars_match(mat,fmla):
    """ Remove the variables bindings from a match. This is used to
    prevent variable capture when applying the match to premises. Make sure free variables
    are not captured by fmla """
    res = dict((s,v) for s,v in mat.iteritems() if il.is_ui_sort(s))
    sympairs = [(s,v) for s,v in mat.iteritems() if il.is_constant(s)]
    symfmlas = il.rename_vars_no_clash([v for s,v in sympairs],[fmla])
    res.update((s,w) for (s,v),w in zip(sympairs,symfmlas))
    return res


def show_match(m):
    if m is None:
        print 'no match'
        return 
    print 'match {'
    for x,y in m.iteritems():
        print '{} : {} |-> {}'.format(x,x.sort if hasattr(x,'sort') else 'type',y)
    print '}'
        
def match_problem(schema,decl):
    """ Creating a matching problem from a schema and a declaration """
    vocab = goal_vocab(schema)
    freesyms = set(vocab.symbols + vocab.sorts + vocab.variables)
    constants = set(v for v in goal_free(decl) if il.is_variable(v))
    return MatchProblem(schema,goal_conc(schema),goal_conc(decl),freesyms,constants)

def transform_defn_schema(schema,decl):
    """ Transform definition schema to match a definition. """
    conc = goal_conc(schema)
    decl = goal_conc(decl)
    if not(isinstance(decl,il.Definition) and isinstance(conc,il.Definition)):
        return schema
    declargs = decl.lhs().args
    concargs = conc.lhs().args
    if len(declargs) > len(concargs):
        schema = parameterize_schema([x.sort for x in declargs[:len(declargs)-len(concargs)]],schema)
    return schema

def transform_defn_match(prob):
    """ Transform a problem of matching definitions to a problem of
    matching the right-hand sides. Requires prob.inst is a definition. """

    schema, conc,decl,freesyms = prob.schema, prob.pat,prob.inst,prob.freesyms
    if not(isinstance(decl,il.Definition) and isinstance(conc,il.Definition)):
        return prob
    declsym = decl.defines()
    concsym = conc.defines()
    # dmatch = match(conc.lhs(),decl.lhs(),freesyms)
    # if dmatch is None:
    #     print "left-hand sides didn't match: {}, {}".format(conc.lhs(),decl.lhs())
    #     return None
    declargs = decl.lhs().args
    concargs = conc.lhs().args
    if len(declargs) < len(concargs):
        return None
    declrhs = decl.rhs()
    concrhs = conc.rhs()
    vmap = dict((x.name,y.resort(x.sort)) for x,y in zip(concargs,declargs))
    concrhs = lu.substitute_ast(concrhs,vmap)
    dmatch = {concsym:declsym}
    for x,y in zip(func_sorts(concsym),func_sorts(declsym)):
        if x in freesyms:
            if x in dmatch and dmatch[x] != y:
                print "lhs sorts didn't match: {}, {}".format(x,y)
                return None
            dmatch[x] = y
        else:
            if x != y:
                print "lhs sorts didn't match: {}, {}".format(x,y)
                return None
    concrhs = apply_match(dmatch,concrhs)
    freesyms = apply_match_freesyms(dmatch,freesyms)
    freesyms = [x for x in freesyms if x not in concargs]
    constants = set(x for x in prob.constants if x not in declargs)
    vvmap = dict((x,y.resort(x.sort)) for x,y in zip(concargs,declargs))
    schema = apply_match_goal(vvmap,schema,apply_match_alt)
    schema = apply_match_goal(dmatch,schema,apply_match_alt)
    return MatchProblem(schema,concrhs,declrhs,freesyms,constants)

def goal_prems_by_name(goal):
    gprems = goal_prem_goals(goal)
    return dict((p.name,p) for p in gprems)

def add_prem_match(proof_match,prob,goal,context):
    sprems = goal_prems_by_name(prob.schema)
    pats = []
    insts = []
    new_match = []
    for m in proof_match:
        lhs,rhs = m.args
        if isinstance(lhs,ia.Atom) and len(lhs.args) == 0:
            sprem = sprems.get(lhs.rep,None)
            if sprem is not None:
                if isinstance(rhs,ia.Atom) and len(rhs.args) == 0:
                    gprem = context.lookup_schema(rhs.rep,goal,rhs)
                    pats.append(sprem)
                    insts.append(gprem)
                    continue
        new_match.append(m)
    if pats:
        pat = ia.Tuple(*(pats + [prob.pat]))
        inst = ia.Tuple(*(insts + [prob.inst]))
        prob = MatchProblem(prob.schema,pat,inst,prob.freesyms,prob.constants,pats)
    return new_match,prob

def parameterize_schema(sorts,schema):
    """ Add initial parameters to all the free symbols in a schema.

    Takes a list of sorts and an ia.SchemaBody. """

    vars = make_distinct_vars(sorts,goal_conc(schema))
    match = {}
    prems = []
    for prem in goal_prems(schema):
        if isinstance(prem,ia.ConstantDecl):
            sym = prem.args[0]
            vs2 = [il.Variable('X'+str(i),y) for i,y in enumerate(sym.sort.dom)]
            sym2 = sym.resort(il.FuncConstSort(*(sorts + list(sym.sort.dom) + [sym.sort.rng])))
            match[sym] = il.Lambda(vs2,sym2(*(vars+vs2)))
            prems.append(ia.ConstantDecl(sym2))
        else:
            prems.append(prem)
    conc = apply_match(match,goal_conc(schema))
    return clone_goal(schema,prems,conc)

# A schema instantiataion has an associated list of mathces
# (following 'with').  When compiling this, the left-hand sides
# use names of constants and variables from the shema being
# instantiated, while the right-hand sides uses names from the
# current goal (and both may use names from the globla context

def compile_match_list(proof_match,left_goal,right_goal,allow_witness=False):
    def compile_match(d):
        x,y = d.lhs(),d.rhs()
        x = compile_expr_vocab(x,left_goal_vocab)
        y = compile_expr_vocab(y,right_goal_vocab)
        return ia.Definition(x,y)
    left_goal_vocab = goal_vocab(left_goal)
    right_goal_vocab = goal_vocab(right_goal)
    if allow_witness:
        left_goal_vocab.variables.extend(list(logic_util.used_variables(goal_conc(left_goal))))
    return [compile_match(d) for d in proof_match]

# A "match" is a map from symbols to lambda terms
    
def compile_one_match(lhs,rhs,freesyms,constants):
    if il.is_variable(lhs):
        return fo_match(lhs,rhs,freesyms,constants)
    if not isinstance(rhs,il.UninterpretedSort):
        rhsvs = dict((v.name,v) for v in lu.used_variables_ast(rhs))
        vmatches = [{v.sort:rhsvs[v.name].sort} for v in lu.used_variables_ast(lhs)
                    if v.name in rhsvs and v.sort in freesyms]
        vmatch = merge_matches(*vmatches)
        if vmatch is None:
            return None
        lhs = apply_match_alt(vmatch,lhs)
        newfreesyms = apply_match_freesyms(vmatch,freesyms)
        somatch = match(lhs,rhs,newfreesyms,constants)
        if somatch is None:
            return None
        somatch = compose_matches(freesyms,vmatch,somatch,vmatch)
        fmatch = merge_matches(vmatch,somatch)
        return fmatch
    else:
        return match_sort(lhs,rhs,freesyms)


def compile_match(proof_match,prob,decl,allow_witness=False):
    """ Compiles match in a proof. Only the symbols in
    freesyms may be used in the match."""

    schema = prob.schema
    freesyms = prob.freesyms.copy()
    if allow_witness:
        freesyms.update(logic_util.used_variables(goal_conc(schema)))
    matches = compile_match_list(proof_match,schema,decl,allow_witness=allow_witness)
    matches = [compile_one_match(m.lhs(),m.rhs(),freesyms,prob.constants) for m in matches]
    res = merge_matches(*matches)
    return res
        
        
    res = dict()
    for m in proof_match:
        if il.is_app(m.lhs()):
            res[m.defines()] = il.Lambda(m.lhs().args,m.rhs())
        else:
            res[m.lhs()] = m.rhs()
    # iu.dbg('freesyms')
    # freesyms = apply_match_freesyms(res,freesyms)
    # iu.dbg('freesyms')
    # for sym in res:
    #     if sym not in freesyms:
    #         raise ProofError(proof,'{} is not a premise of schema {}'.format(repr(sym),schemaname))
    return res

def match_rhs_vars(match):
    """ Get the symbols occurring free on the right-hand side of a match """
    res = set()
    for w in match.values():
        for v in w if isinstance(w,list) else [w]:
            if isinstance(v,(il.UninterpretedSort,il.EnumeratedSort)):
                res.add(v)
            else:
                res.update(fmla_vocab(v))
    return res

def is_lambda(p):
    return isinstance(p,ia.ConstantDecl) and isinstance(p.args[0],il.Lambda)

def apply_match_goal(match,x,apply_match,env = None):
    """ Apply a match to a goal """
    env = env if env is not None else set()
    if isinstance(x,ia.LabeledFormula):
        fmla = x.formula
        if isinstance(fmla,ia.SchemaBody):
            bound = [s for s in goal_defns(x) if s not in match]
            with il.BindSymbols(env,bound):
                prems = [apply_match_goal(match,y,apply_match,env) for y in fmla.prems()]
                prems = [p for p in prems if not is_lambda(p)]
                fmla = fmla.clone(prems+[apply_match(match,fmla.conc(),env)])
        else:
            fmla = apply_match(match,fmla,env)
        g = x.clone([x.label,fmla])
        return g
    if isinstance(x,(il.UninterpretedSort,il.EnumeratedSort)):
        return apply_match_sort(match,x)
    else:
        return x.clone([apply_match_func_alt(match,x.args[0],env)])

def apply_match_match(match,orig_match,apply_match):
    """ Apply a match match to match orig_match. Applying the resulting match should
    have the same effect as apply first orig_match, then match. """
    orig_match = dict((x,apply_match(match,y)) for x,y in orig_match.iteritems())
    orig_match.update((x,y) for x,y in match.iteritems() if x not in orig_match)
    return orig_match

def apply_match_to_problem(match,prob,apply_match):
    avoid_capture_problem(prob,match)
    prob.schema = apply_match_goal(match,prob.schema,apply_match)
    prob.pat = apply_match(match,prob.pat)
    prob.freesyms = apply_match_freesyms(match,prob.freesyms)
    prob.revmap = dict((x,y) for x,y in prob.revmap.iteritems() if x not in match)

def rename_problem(match,prob):
    prob.schema = apply_match_goal(match,prob.schema,apply_match_alt)
    prob.pat = apply_match_alt(match,prob.pat)
    prob.freesyms = set(match.get(sym,sym) for sym in prob.freesyms)
    prob.revmap.update((y,x) for x,y in match.iteritems())

def avoid_capture_problem(prob,match):
    """ Rename a match problem to avoid capture when applying a
    match"""
    mrv = match_rhs_vars(match)
    matchnames = set(x.name for x in match_rhs_vars(match))
    used = set(matchnames)
    used.update(x.name for x in goal_defns(prob.schema))
    used.update(v.name for v in goal_free(prob.schema) if il.is_variable(v))
    rn = iu.UniqueRenamer(used=used)
    cmatch = dict((v,v.rename(rn)) for v in prob.freesyms
                  if v.name in matchnames and v not in match)
    rename_problem(cmatch,prob)

def detect_nonce_symbols(prob):
    """ Make sure that no nonce symbols produced by
    avoid_capture_problem appear free after matching. This is done to
    avoid nonce symbols becoming visible to the user. If one of these
    remains after matching, we report the original symbol
    as clashing with the corresponding symbol in the goal."""

    for sym in prob.revmap.values():
        raise CaptureError(None,'Symbol {} in schema clashes with {} in goal.\nSuggest renaming or instantiating it.'.format(sym,sym))

def trivial_goal(goal):
    """ A goal is trivial if the conclusion is equal to one of the premises modulo
    alpha conversion """
    conc = goal_conc(goal)
    for prem in goal_prem_goals(goal):
        if len(goal_prems(prem)) == 0:
            if il.equal_mod_alpha(goal_conc(prem),conc):
                return True
    return False

# Test whether two goals are equivalent mod alpha renaming
# TODO: for now just tests syntactic equality

def goals_eq_mod_alpha(x,y):
    if isinstance(x.formula,ia.SchemaBody):
        if not isinstance(y.formula,ia.SchemaBody):
            return False
        xps, yps = goal_prems(x), goal_prems(y)
        if len(xps) != len(yps):
            return False
        for xp,yp in zip(xps,yps):
            if type(xp) is not type(yp):
                return False
            if isinstance(xp,ia.LabeledFormula):
                if not goals_eq_mod_alpha(xp,yp):
                    return False
            elif isinstance(xp,ia.ConstantDecl):
                if xp.args[0] != yp.args[0]:
                    return False
            elif isinstance(xp,il.UninterpretedSort):
                if xp != yp:
                    return False
    else:
        if isinstance(y.formula,ia.SchemaBody):
            return False
    return il.equal_mod_alpha(goal_conc(x),goal_conc(y))

def apply_match(match,fmla,env = None):
    """ apply a match to a formula. 

    In effect, substitute all symbols in the match with the
    corresponding lambda terms and apply beta reduction

    Have to first alpha-rename to avoid capture of variables by binders

    """
    freevars = match_rhs_vars(match)
    fmla = il.alpha_avoid(fmla,freevars)
    return apply_match_rec(match,fmla,env if env is not None else set())

def apply_match_rec(match,fmla,env):
    args = [apply_match_rec(match,f,env) for f in fmla.args]
    if il.is_app(fmla):
        if fmla.rep in match:
            func = match[fmla.rep]
            return func(*args)
        return apply_match_func(match,fmla.rep)(*args)
    if il.is_variable(fmla) and fmla in match:
        return match[fmla]
    if il.is_binder(fmla):
        with il.BindSymbols(env,fmla.variables):
            fmla = fmla.clone_binder([apply_match_rec(match,v,env) for v in fmla.variables],args[0])
        return fmla
    return fmla.clone(args)

def raise_capture(v):
    raise CaptureError(None,'symbol {} is captured in substitution'.format(v))

def match_get(match,sym,env,default=None):
    """ get the value of a symbol in a match, checking that no symbols
    are captured in env """
    val = match.get(sym,None)
    if isinstance(val,list):  # for unfolding only, may get a list of values
        save = val
        val = val[0]
        if len(save) > 1:
            del save[0]
    if val is not None:
        vocab = lu.used_symbols_ast(val)
        vocab.update(lu.variables_ast(val))
        for v in vocab:
            if v in env:
                raise_capture(v)
        return val
    return default
    

def apply_match_alt(match,fmla,env = None):
    """ apply a match to a formula. 

    In effect, substitute all symbols in the match with the
    corresponding lambda terms and apply beta reduction

    If present, env is list of symbols bound in the environment.
    Substituting one of these symbols into the formula will be considered
    capture and cause CaptureError to be raised.

    """
    freevars = list(match_rhs_vars(match))
    fmla = il.alpha_avoid(fmla,freevars)
    return apply_match_alt_rec(match,fmla,env if env is not None else set())


def apply_fun(fun,args):
    try:
        return fun(*args)
    except il.CaptureError as err:
        for sym in err.variables:
            raise_capture(sym)

def apply_match_alt_rec(match,fmla,env):
    args = [apply_match_alt_rec(match,f,env) for f in fmla.args]
    if il.is_app(fmla):
        if fmla.rep in match:
            return apply_fun(match_get(match,fmla.rep,env),args)
        func = apply_match_func(match,fmla.rep)
        func = match_get(match,func,env,func)
        return func(*args)
    if il.is_variable(fmla):
        if fmla in match:
            return match_get(match,fmla,env)
        fmla = il.Variable(fmla.name,apply_match_sort(match,fmla.sort))
        fmla = match_get(match,fmla,env,fmla)
        return fmla
    if il.is_binder(fmla):
        with il.BindSymbols(env,fmla.variables):
            fmla = fmla.clone_binder([apply_match_alt_rec(match,v,env) for v in fmla.variables],args[0])
        return fmla
    return fmla.clone(args)

def apply_match_func(match,func):
    sorts = func_sorts(func)
    sorts = [match.get(s,s) for s in sorts]
    return il.Symbol(func.name,sorts[0] if len(sorts) == 1 else il.FunctionSort(*sorts))

def apply_match_func_alt(match,func,env):
    if il.is_lambda(func):
        return apply_match_alt(match,func,env)
    if func in match:
        return match[func]
    func = apply_match_func(match,func)
    return match.get(func,func)

def apply_match_sym(match,sym):
    if il.is_variable(sym):
        return il.Variable(sym.name,match.get(sym.sort,sym.sort))
    return match.get(sym,sym) if isinstance(sym,il.UninterpretedSort) else apply_match_func(match,sym)

def apply_match_sort(match,sort):
    return match.get(sort,sort)

def apply_match_freesyms(match,freesyms):
    return set(apply_match_sym(match,sym) for sym in freesyms if sym not in match)

def apply_match_freesyms_alt(match,freesyms):
    msyms = [apply_match_sym(match,sym) for sym in freesyms]
    return [sym for sym in msyms if sym not in match]

def func_sorts(func):
    return list(func.sort.dom) + [func.sort.rng]

def lambda_sorts(lmbd):
    return [v.sort for v in lmbd.variables] + [lmbd.body.sort]

def term_sorts(term):
    """ Returns a list of the domain and range sorts of the head function of a term, if any """
    return func_sorts(term.rep) if il.is_app(term) else [term.sort] if il.is_variable(term) else []

def funcs_match(pat,inst,freesyms):
    psorts,isorts = map(func_sorts,(pat,inst))
    res = (pat.name == inst.name and len(psorts) == len(isorts)
            and all(x == y for x,y in zip(psorts,isorts) if x not in freesyms))
    return res
    
def heads_match(pat,inst,freesyms):
    """Returns true if the heads of two terms match. This means they have
    the same top-level operator and same number of
    arguments. Quantifiers do not match anything. A function symbol matches
    if it has the same name and if it agrees on the non-free sorts in
    its type.
    """
    return (il.is_app(pat) and il.is_app(inst) and funcs_match(pat.rep,inst.rep,freesyms) and pat.rep not in freesyms
        or not il.is_app(pat) and not il.is_quantifier(pat)
           and type(pat) is type(inst) and len(pat.args) == len(inst.args))
    
def make_distinct_vars(sorts,*asts):
    vars = [il.Variable('V'+str(i),sort) for i,sort in enumerate(sorts)]
    return lu.rename_variables_distinct_asts(vars,asts)
    

def extract_terms(inst,terms):
    """ Returns a lambda term t such that t(terms) = inst and
    terms do not occur in t. vars is a list of distinct variables
    of same types as terms that are not free in inst. """

    vars = make_distinct_vars([t.sort for t in terms], inst)
    def rec(inst):
        for term,var in zip(terms,vars):
            if term == inst:
                return var
        return inst.clone(map(rec,inst.args))
    return il.Lambda(vars,rec(inst))

def fo_match(pat,inst,freesyms,constants):
    """ Compute a partial first-order match. Matches free FO variables to ground terms,
    but ignores variable occurrences under free second-order symbols. """

    if il.is_variable(pat):
        if pat in freesyms and all(x in constants for x in lu.variables_ast(inst)):
            res = {pat:inst}
            if pat.sort in freesyms:
                res[pat.sort] = inst.sort
                return res
            if pat.sort == inst.sort:
                return res
    if il.is_quantifier(pat) and il.is_quantifier(inst):
        with RemoveSymbols(freesyms,pat.variables):
            return fo_match(pat.body,inst.body,freesyms,constants)
    if heads_match(pat,inst,freesyms):
        matches = [fo_match(x,y,freesyms,constants) for x,y in zip(pat.args,inst.args)]
        res =  merge_matches(*matches)
        return res
    return dict()
    
            

def match(pat,inst,freesyms,constants):
    """ Match an instance to a pattern.

    A match is an assignment sigma to freesyms such
    that sigma pat =_alpha inst.

    """

    if il.is_quantifier(pat):
        return match_quants(pat,inst,freesyms,constants)
    if heads_match(pat,inst,freesyms):
        matches = [match(x,y,freesyms,constants) for x,y in zip(pat.args,inst.args)]
        matches.extend([match_sort(x,y,freesyms) for x,y in zip(term_sorts(pat),term_sorts(inst))])
        if il.is_variable(pat):
            matches.append({pat:inst})
        res = merge_matches(*matches)
        return res
    elif il.is_app(pat) and pat.rep in freesyms:
        B = extract_terms(inst,pat.args)
        if all(v in constants for v in lu.variables_ast(B)):
            matches = [{pat.rep:B}]
            matches.extend([match_sort(x,y,freesyms) for x,y in zip(term_sorts(pat),lambda_sorts(B))])
            res = merge_matches(*matches)
            return res
        


def match_quants(pat,inst,freesyms,constants):
    """ Match an instance to a pattern that is a quantifier.
    """

    if type(pat) is not type(inst) or len(pat.variables) != len(inst.variables):
        return None
    with AddSymbols(freesyms,pat.variables):
        matches = [match(x,y,freesyms,constants) for x,y in zip(pat.variables,inst.variables)]
        mat = merge_matches(*matches)
        if mat is not None:
            mbody = apply_match(mat,pat.body)
            bodyfreesyms = apply_match_freesyms(mat,freesyms)
            bodymat = match(mbody,inst.body,bodyfreesyms,constants)
            bodymat = compose_matches(freesyms,mat,bodymat,pat.variables)
            mat = merge_matches(mat,bodymat)
#        matches.append(match(pat.body,inst.body,freesyms,constants))
#        mat = merge_matches(*matches)
        if mat is not None:
            for x in pat.variables:
                if x in mat:
                    del mat[x]
        return mat

def compose_matches(freesyms,mat1,mat2,quants):
    if mat1 is None or mat2 is None:
        return None
    res = dict()
    for sym in freesyms:
        if sym not in quants:
            sym1 = apply_match_sym(mat1,sym)
            if sym1 in mat2:
                res[sym] = mat2[sym1]
    return res

def match_sort(pat,inst,freesyms):
    if pat in freesyms:
        return {pat:inst}
    return dict() if pat == inst else None

def merge_matches(*matches):
    if len(matches) == 0:
        return dict()
    if any(match is None for match in matches):
        return None
    res = dict(matches[0].iteritems())
    for match2 in matches[1:]:
        for sym,lmda in match2.iteritems():
            if sym in res:
                if not equiv_alpha(lmda,res[sym]):
                    return None
            else:
                res[sym] = lmda
    return res

def equiv_alpha(x,y):
    """check if two closed terms are equivalent module alpha
    conversion. for now, we assume the terms are closed
    """
    if x == y:
        return True
    if il.is_lambda(x) and il.is_lambda(y):
        return x.body == il.substitute(y.body,zip(x.variables,y.variables))
    return False
    pass

# Convert a goal to skolem normal form. This means the premises are in
# universal prenex form and the conclusion is in existential prenex
# form.

def skolemize_goal(goal):
    var_uniq = il.VariableUniqifier()
    vocab = goal_vocab(goal)
    used_names = set(x.name for x in vocab.symbols)
    used_names.update(x.name for x in goal_free(goal))
    renamer = iu.UniqueRenamer(used = used_names)
    skfuns = []
    def rec(goal,pos):
        if not isinstance(goal,ia.LabeledFormula):
            return goal
        prems = [rec(prem,not pos) for prem in goal_prems(goal)]
        conc = skolemize_fmla(goal_conc(goal),pos,renamer,skfuns)
        return clone_goal(goal,prems,conc)
    goal = rec(goal,True)
    return clone_goal(goal,[ia.ConstantDecl(s) for s in skfuns]+goal_prems(goal), goal_conc(goal))


def skolemize_fmla(fmla,pos,renamer,skfuns):
    univs = []
    outer = []
    var_uniq = il.VariableUniqifier(used=renamer.used) # don't capture any free symbols!
    def rec( fmla,pos):
        if isinstance(fmla,il.Not):
            return fmla.clone([rec(fmla.args[0],not pos)])
        if isinstance(fmla,il.Implies):
            return fmla.clone([
                rec(fmla.args[0],not pos),
                rec(fmla.args[1],pos),
            ])
        if isinstance(fmla,(il.And,il.Or)):
            return fmla.clone([rec(arg,pos) for arg in fmla.args])
        is_e = il.is_exists(fmla)
        is_a = il.is_forall(fmla)
        if is_a and pos or is_e and not pos:
            fvs = list(x for x in iu.unique(lu.variables_ast(fmla)) if x in outer)
            body = fmla.body
            for v in fmla.variables:
                sym = il.Symbol(renamer('_'+v.name),
                                il.FuncConstSort(*([w.sort for w in fvs] + [v.sort])))
                term = sym(*fvs) if fvs else sym
                skfuns.append(sym)
                body =  il.substitute(body,[(v,term)])
            return rec(body,pos)
        if is_e and pos or is_a and not pos:
            body = fmla.body
            for v in fmla.variables:
                u = var_uniq(v)
                univs.append(u)
                outer.append(u)
                body = il.substitute(body,[(v,u)])
            res = rec(body,pos)
            for v in fmla.variables:
                outer.pop()
            return res
        if isinstance(fmla,ia.TemporalModels):
            return fmla.clone([rec(fmla.args[0],pos)])
        return fmla
    body = rec(fmla,pos)
    if univs:
        quant = il.Exists if pos else il.ForAll
        if isinstance(body,ia.TemporalModels):
            body = body.clone([quant(univs,body.args[0])])
        else:
            body = quant(univs,body)
    return body

def compile_witness_list(proof,goal):
#    the_goal_vocab = goal_vocab(goal,get_bound_vars=True)
    the_goal_vocab = goal_vocab(goal)
    the_goal_vocab.variables.extend(list(logic_util.used_variables(goal_conc(goal))))
    return [compile_expr_vocab(d,the_goal_vocab) for d in proof.args]
    
def compile_with_goal_vocab(expr,goal):
#    the_goal_vocab = goal_vocab(goal,get_bound_vars=True)
    the_goal_vocab = goal_vocab(goal)
#    the_goal_vocab.variables.extend(list(logic_util.used_variables(goal_conc(goal))))
    return compile_expr_vocab_ext(expr,the_goal_vocab)

def match_from_defn(defn):
    vs = set()
    defn = defn.formula
    while isinstance(defn,il.ForAll):
        vs.update(defn.variables)
        defn = defn.body
    if il.is_eq(defn) or isinstance(defn,il.Iff):
        lhs,rhs = defn.args
        if il.is_app(lhs) & (all(x in vs for x in lhs.args) or True):
            if iu.distinct(lhs.args):
                return {lhs.rep : il.Lambda(lhs.args,rhs)}
    raise ProofError(defn,'not a definition')

def match_from_defns(defns):
    matches = [match_from_defn(d) for d in  defns]
    lhs = list(matches[0].keys())[0]
    assert all(lhs in m for m in matches)
    return {lhs:[m[lhs] for m in matches]}

def unfold_goal(goal,defns):
    for rdefs in defns:
        match = match_from_defns(rdefs)
        goal = apply_match_goal(match,goal,apply_match_alt)
    return goal

def unfold_fmla(fmla,defns):
    for rdefs in defns:
        match = match_from_defns(rdefs)
        fmla = apply_match_alt(match,fmla)
    return fmla

def goal_apply_to_prem(goal,premname,fn):
    prems = goal_prems(goal)
    premmap = dict((x.name,idx) for idx,x in enumerate(prems))
    if premname in premmap:
        idx = premmap[premname]
        prem = prems[idx]
        if not isinstance(prem,ia.LabeledFormula):
            return None
        return clone_goal(goal,prems[0:idx]+[fn(prems[idx])]+prems[idx+1:],goal_conc(goal))
    return None

def goal_apply_to_conc(goal,fn):
    return clone_goal(goal,goal_prems(goal),fn(goal_conc(goal)))

# When instantiating a schema, unmatched free variables occurring only
# in the conclusion can be universally quantified. 

def close_unmatched(goal,match):
    conc = goal_conc(goal)
    prem_vars = lu.used_variables_asts(goal_prem_goals(goal))
    conc_vars = [x for x in iu.unique(lu.variables_ast(conc))
                 if x not in match and x not in prem_vars]
    for v in reversed(conc_vars):
        conc = il.ForAll([v],conc)
    return clone_goal(goal,goal_prems(goal),conc)

# When instantiating a schema, we drop the premises that supplied in the
# proof goal. 

def drop_supplied_prems(schema,goal,proof_match):
    gprems = goal_prems_by_name(goal)
    pmap = dict()
    for m in proof_match:
        lhs,rhs = m.args
        if isinstance(lhs,ia.Atom) and len(lhs.args) == 0:
            if isinstance(rhs,ia.Atom) and len(rhs.args) == 0:
                pmap[lhs.rep] = rhs.rep
    def is_supplied(prem):
        if isinstance(prem,ia.LabeledFormula) and prem.name in pmap:
            gname = pmap[prem.name]
            return gname in gprems and goals_eq_mod_alpha(prem,gprems[gname])
        return False
    return clone_goal(schema,[x for x in goal_prems(schema) if not is_supplied(x)],
                      goal_conc(schema))

# Remove the "explicit" tag from a goal

def remove_explicit(goal):
    if hasattr(goal,'explicit') and goal.explicit:
        goal = goal.clone(goal.args)
        goal.explicit = False
    return goal

class AddSymbols(object):
    """ temporarily add some symbols to a set of symbols """
    def __init__(self,symset,symlist):
        self.symset,self.symlist = symset,list(symlist)
    def __enter__(self):
        global sig
        self.saved = []
        for sym in self.symlist:
            if sym in self.symset:
                self.saved.append(sym)
                self.remove(sym)
            self.symset.add(sym)
        return self
    def __exit__(self,exc_type, exc_val, exc_tb):
        global sig
        for sym in self.symlist:
            self.symset.remove(sym)
        for sym in self.saved:
            self.symset.add(sym)
        return False # don't block any exceptions

class RemoveSymbols(object):
    """ temporarily add some symbols to a set of symbols """
    def __init__(self,symset,symlist):
        self.symset,self.symlist = symset,list(symlist)
    def __enter__(self):
        global sig
        self.saved = []
        for sym in self.symlist:
            if sym in self.symset:
                self.saved.append(sym)
                self.remove(sym)
        return self
    def __exit__(self,exc_type, exc_val, exc_tb):
        global sig
        for sym in self.saved:
            self.symset.add(sym)
        return False # don't block any exceptions

registered_tactics = dict()

def register_tactic(name,tactic):
    registered_tactics[name] = tactic
