/*++
Copyright (c) 2013 Microsoft Corporation

Module Name:

    sorting_network.h

Abstract:

    Utility for creating a sorting network.

Author:

    Nikolaj Bjorner (nbjorner) 2013-11-07

Notes:

    Same routine is used in Formula.

--*/

#include "util/vector.h"

#ifndef SORTING_NETWORK_H_
#define SORTING_NETWORK_H_

    template <typename Ext>
    class sorting_network {
        typedef typename Ext::vector vect;
        Ext&               m_ext;
        svector<unsigned>  m_currentv;
        svector<unsigned>  m_nextv;
        svector<unsigned>* m_current;
        svector<unsigned>* m_next;

        unsigned& current(unsigned i) { return (*m_current)[i]; }
        unsigned& next(unsigned i) { return (*m_next)[i]; }
       
        void exchange(unsigned i, unsigned j, vect& out) {
            SASSERT(i <= j);
            if (i < j) {
                typename Ext::T ei = out.get(i);
                typename Ext::T ej = out.get(j);
                out.set(i, m_ext.mk_ite(m_ext.mk_le(ei, ej), ei, ej));
                out.set(j, m_ext.mk_ite(m_ext.mk_le(ej, ei), ei, ej));
            }
        }
        
        void sort(unsigned k, vect& out) {
            SASSERT(is_power_of2(k) && k > 0);
            if (k == 2) {
                for (unsigned i = 0; i < out.size()/2; ++i) {
                    exchange(current(2*i), current(2*i+1), out);
                    next(2*i) = current(2*i);
                    next(2*i+1) = current(2*i+1);
                }
                std::swap(m_current, m_next);
            }
            else {
                
                for (unsigned i = 0; i < out.size()/k; ++i) {
                    unsigned ki = k * i;
                    for (unsigned j = 0; j < k / 2; ++j) {
                        next(ki + j) = current(ki + (2 * j));
                        next(ki + (k / 2) + j) = current(ki + (2 * j) + 1);
                    }
                }
                
                std::swap(m_current, m_next);
                sort(k / 2, out);
                for (unsigned i = 0; i < out.size() / k; ++i) {
                    unsigned ki = k * i;
                    for (unsigned j = 0; j < k / 2; ++j) {
                        next(ki + (2 * j)) = current(ki + j);
                        next(ki + (2 * j) + 1) = current(ki + (k / 2) + j);
                    }
                    
                    for (unsigned j = 0; j < (k / 2) - 1; ++j) {
                        exchange(next(ki + (2 * j) + 1), next(ki + (2 * (j + 1))), out);
                    }
                }
                std::swap(m_current, m_next);
            }
        }        

        bool is_power_of2(unsigned n) const {
            return n != 0 && ((n-1) & n) == 0;
        }
        
    public:
        sorting_network(Ext& ext):
            m_ext(ext),
            m_current(&m_currentv),
            m_next(&m_nextv)
        {}
        
        void operator()(vect const& in, vect& out) {
            out.reset();
            out.append(in);
            if (in.size() <= 1) {
                return;
            }
            while (!is_power_of2(out.size())) {
                out.push_back(m_ext.mk_default());
            }
            for (unsigned i = 0; i < out.size(); ++i) {
                m_currentv.push_back(i);
                m_nextv.push_back(i);
            }
            unsigned k = 2;
            while (k <= out.size()) {
                sort(k, out);
                k *= 2;
            }
        }        
    };

    // parametric sorting network
    // Described in Abio et.al. CP 2013.
    template<class psort_expr>
    class psort_nw {
        typedef typename psort_expr::literal literal;
        typedef typename psort_expr::literal_vector literal_vector;

        class vc {
            unsigned v; // number of vertices
            unsigned c; // number of clauses
            static const unsigned lambda = 5;
        public:
            vc(unsigned v, unsigned c):v(v), c(c) {}

            bool operator<(vc const& other) const {
                return to_int() < other.to_int();
            }
            vc operator+(vc const& other) const {
                return vc(v + other.v, c + other.c);
            }
            unsigned to_int() const {
                return lambda*v + c;
            }
            vc operator*(unsigned n) const {
                return vc(n*v, n*c);
            }
        };

        static vc mk_min(vc const& v1, vc const& v2) {
            return (v1.to_int() < v2.to_int())?v1:v2;
        }


        enum cmp_t { LE, GE, EQ, GE_FULL, LE_FULL };
        psort_expr&  ctx;
        cmp_t        m_t;

        // for testing
        static const bool m_disable_dcard    = false;
        static const bool m_disable_dsorting = false;
        static const bool m_disable_dsmerge  = false;
        static const bool m_force_dcard      = false;
        static const bool m_force_dsorting   = false;
        static const bool m_force_dsmerge    = false;

    public:
        struct stats {
            unsigned m_num_compiled_vars;
            unsigned m_num_compiled_clauses;
            unsigned m_num_clause_vars;
            void reset() { memset(this, 0, sizeof(*this)); }
            stats() { reset(); }
        };
        stats        m_stats;

        struct scoped_stats {
            stats& m_stats;
            stats  m_save;
            unsigned m_k, m_n;
            scoped_stats(stats& st, unsigned k, unsigned n): m_stats(st), m_save(st), m_k(k), m_n(n) {}
            ~scoped_stats() {
                IF_VERBOSE(1, 
                           verbose_stream() << "k: " << m_k << " n: " << m_n;
                           verbose_stream() << " clauses: " << m_stats.m_num_compiled_clauses - m_save.m_num_compiled_clauses;
                           verbose_stream() << " vars: " << m_stats.m_num_clause_vars - m_save.m_num_clause_vars;
                           verbose_stream() << " clauses: " << m_stats.m_num_compiled_clauses;
                           verbose_stream() << " vars: " << m_stats.m_num_clause_vars << "\n";);
            }
        };

        psort_nw(psort_expr& c): ctx(c) {}

        literal ge(bool full, unsigned k, unsigned n, literal const* xs) {
            if (k > n) {
                return ctx.mk_false();
            }
            if (k == 0) {
                return ctx.mk_true();
            }
            SASSERT(0 < k && k <= n);
            literal_vector in, out;
            if (dualize(k, n, xs, in)) {
                return le(full, k, in.size(), in.c_ptr());
            }
            else {
                SASSERT(2*k <= n);
                m_t = full?GE_FULL:GE;
                // scoped_stats _ss(m_stats, k, n);
                psort_nw<psort_expr>::card(k, n, xs, out);                
                return out[k-1]; 
            }
        }
        
        literal le(bool full, unsigned k, unsigned n, literal const* xs) {
            if (k >= n) {
                return ctx.mk_true();
            }
            SASSERT(k < n);
            literal_vector in, out;
            if (dualize(k, n, xs, in)) {
                return ge(full, k, n, in.c_ptr());
            }
            else if (k == 1) {
                literal_vector ors;
                // scoped_stats _ss(m_stats, k, n);
                return mk_at_most_1(full, n, xs, ors, false);
            }
            else {
                SASSERT(2*k <= n);
                m_t = full?LE_FULL:LE;
                // scoped_stats _ss(m_stats, k, n);
                card(k + 1, n, xs, out);
                return ctx.mk_not(out[k]); 
            }
        }

        literal eq(bool full, unsigned k, unsigned n, literal const* xs) {
            if (k > n) {
                return ctx.mk_false();
            }
            SASSERT(k <= n);
            literal_vector in, out;
            if (dualize(k, n, xs, in)) {
                return eq(full, k, n, in.c_ptr());
            }
            else if (k == 1) {
                // scoped_stats _ss(m_stats, k, n);
                return mk_exactly_1(full, n, xs);
            }
            else {
                // scoped_stats _ss(m_stats, k, n);
                SASSERT(2*k <= n);
                m_t = EQ;
                card(k+1, n, xs, out);
                SASSERT(out.size() >= k+1);
                if (k == 0) {
                    return ctx.mk_not(out[k]);
                }
                else {
                    return ctx.mk_min(out[k-1], ctx.mk_not(out[k]));
                }
            }
        }

        
    private:

        void add_implies_or(literal l, unsigned n, literal const* xs) {
            literal_vector lits(n, xs);
            lits.push_back(ctx.mk_not(l));
            add_clause(lits);
        }

        void add_or_implies(literal l, unsigned n, literal const* xs) {
            for (unsigned j = 0; j < n; ++j) {
                add_clause(ctx.mk_not(xs[j]), l);
            }
        }

        literal mk_or(unsigned n, literal const* ors) {
            if (n == 1) {
                return ors[0];
            }
            literal result = fresh();
            add_implies_or(result, n, ors);
            add_or_implies(result, n, ors);
            return result;
        }

        literal mk_or(literal l1, literal l2) {
            literal ors[2] = { l1, l2 };
            return mk_or(2, ors);
        }
        literal mk_or(literal_vector const& ors) {
            return mk_or(ors.size(), ors.c_ptr());
        }

        void add_implies_and(literal l, literal_vector const& xs) {
            for (unsigned j = 0; j < xs.size(); ++j) {
                add_clause(ctx.mk_not(l), xs[j]);
            }
        }

        void add_and_implies(literal l, literal_vector const& xs) {
            literal_vector lits;
            for (unsigned j = 0; j < xs.size(); ++j) {
                lits.push_back(ctx.mk_not(xs[j]));
            }
            lits.push_back(l);
            add_clause(lits);
        }

        literal mk_and(literal l1, literal l2) {
            literal_vector xs;
            xs.push_back(l1); xs.push_back(l2);
            return mk_and(xs);
        }

        literal mk_and(literal_vector const& ands) {
            if (ands.size() == 1) {
                return ands[0];
            }
            literal result = fresh();
            add_implies_and(result, ands);
            add_and_implies(result, ands);
            return result;
        }

        literal mk_exactly_1(bool full, unsigned n, literal const* xs) {
            literal_vector ors;
            literal r1 = mk_at_most_1(full, n, xs, ors, true);

            if (full) {
                r1 = mk_and(r1, mk_or(ors));
            }
            else {
                add_implies_or(r1, ors.size(), ors.c_ptr());
            }
            return r1;
        }

        literal mk_at_most_1(bool full, unsigned n, literal const* xs, literal_vector& ors, bool use_ors) {
            TRACE("pb", tout << (full?"full":"partial") << " ";
                  for (unsigned i = 0; i < n; ++i) tout << xs[i] << " ";
                  tout << "\n";);

            if (n >= 4 && false) {
                return mk_at_most_1_bimander(full, n, xs, ors);
            }
            literal_vector in(n, xs);
            literal result = fresh();
            unsigned inc_size = 4;
            literal_vector ands;
            ands.push_back(result);
            while (!in.empty()) {
                ors.reset();
                unsigned n = in.size();
                if (n + 1 == inc_size) ++inc_size;
                for (unsigned i = 0; i < n; i += inc_size) {       
                    unsigned inc = std::min(n - i, inc_size);
                    mk_at_most_1_small(full, inc, in.c_ptr() + i, result, ands);
                    if (use_ors || n > inc_size) {
                        ors.push_back(mk_or(inc, in.c_ptr() + i));
                    }
                }
                if (n <= inc_size) {
                    break;
                }
                in.reset();
                in.append(ors);
            }
            if (full) {
                add_clause(ands);
            }
            return result;
        }

        void mk_at_most_1_small(bool full, unsigned n, literal const* xs, literal result, literal_vector& ands) {
            SASSERT(n > 0);
            if (n == 1) {
                return;
            }
            
            // result => xs[0] + ... + xs[n-1] <= 1
            for (unsigned i = 0; i < n; ++i) {
                for (unsigned j = i + 1; j < n; ++j) {
                    add_clause(ctx.mk_not(result), ctx.mk_not(xs[i]), ctx.mk_not(xs[j]));
                }
            }            

            // xs[0] + ... + xs[n-1] <= 1 => and_x
            if (full) {
                literal and_i = fresh();
                for (unsigned i = 0; i < n; ++i) {
                    literal_vector lits;
                    lits.push_back(and_i);
                    for (unsigned j = 0; j < n; ++j) {
                        if (j != i) lits.push_back(xs[j]);
                    }
                    add_clause(lits);
                }
                ands.push_back(ctx.mk_not(and_i));
            }
        }

        literal mk_at_most_1_small(unsigned n, literal const* xs) {
            SASSERT(n > 0);
            if (n == 1) {
                return ctx.mk_true();
            }

            
#if 0
            literal result = fresh();

            // result => xs[0] + ... + xs[n-1] <= 1
            for (unsigned i = 0; i < n; ++i) {
                for (unsigned j = i + 1; j < n; ++j) {
                    add_clause(ctx.mk_not(result), ctx.mk_not(xs[i]), ctx.mk_not(xs[j]));
                }
            }            

            // xs[0] + ... + xs[n-1] <= 1 => result
            for (unsigned i = 0; i < n; ++i) {
                literal_vector lits;
                lits.push_back(result);
                for (unsigned j = 0; j < n; ++j) {
                    if (j != i) lits.push_back(xs[j]);
                }
                add_clause(lits);
            }

            return result;
#endif
#if 1
            // r <=> and( or(!xi,!xj))
            // 
            literal_vector ands;
            for (unsigned i = 0; i < n; ++i) {
                for (unsigned j = i + 1; j < n; ++j) {
                    ands.push_back(mk_or(ctx.mk_not(xs[i]), ctx.mk_not(xs[j])));
                }                
            }
            return mk_and(ands);
#else
            // r <=> or (and !x_{j != i})

            literal_vector ors;
            for (unsigned i = 0; i < n; ++i) {
                literal_vector ands;
                for (unsigned j = 0; j < n; ++j) {
                    if (j != i) {
                        ands.push_back(ctx.mk_not(xs[j]));
                    }
                }                
                ors.push_back(mk_and(ands));
            }
            return mk_or(ors);
            
#endif
        }

        
        // 

        literal mk_at_most_1_bimander(bool full, unsigned n, literal const* xs, literal_vector& ors) {
            literal_vector in(n, xs);
            literal result = fresh();
            unsigned inc_size = 2;
            literal_vector ands;
            for (unsigned i = 0; i < n; i += inc_size) {                    
                unsigned inc = std::min(n - i, inc_size);
                mk_at_most_1_small(full, inc, in.c_ptr() + i, result, ands);
                ors.push_back(mk_or(inc, in.c_ptr() + i));
            }
            
            unsigned nbits = 0;
            while (static_cast<unsigned>(1 << nbits) < ors.size()) {
                ++nbits;
            }
            literal_vector bits;
            for (unsigned k = 0; k < nbits; ++k) {
                bits.push_back(fresh());
            }
            for (unsigned i = 0; i < ors.size(); ++i) {
                for (unsigned k = 0; k < nbits; ++k) {
                    bool bit_set = (i & (static_cast<unsigned>(1 << k))) != 0;
                    add_clause(ctx.mk_not(result), ctx.mk_not(ors[i]), bit_set ? bits[k] : ctx.mk_not(bits[k]));
                }
            }            
            return result;
        }

        std::ostream& pp(std::ostream& out, unsigned n, literal const* lits) {
            for (unsigned i = 0; i < n; ++i) ctx.pp(out, lits[i]) << " ";
            return out;
        }

        std::ostream& pp(std::ostream& out, literal_vector const& lits) {
            for (unsigned i = 0; i < lits.size(); ++i) ctx.pp(out, lits[i]) << " ";
            return out;
        }

        // 0 <= k <= N
        //     SUM x_i >= k 
        // <=>
        //     SUM ~x_i <= N - k
        // suppose k > N/2, then it is better to solve dual.

        bool dualize(unsigned& k, unsigned N, literal const* xs, literal_vector& in) {
            SASSERT(0 <= k && k <= N);
            if (2*k <= N) {
                return false;
            }
            k = N - k;
            for (unsigned i = 0; i < N; ++i) {
                in.push_back(ctx.mk_not(xs[i]));
            }
            TRACE("pb", 
                  pp(tout << N << ": ", in);                  
                  tout << " ~ " << k << "\n";);
            return true;
        }
        

        bool even(unsigned n) const { return (0 == (n & 0x1)); }
        bool odd(unsigned n) const { return !even(n); }
        unsigned ceil2(unsigned n) const { return n/2 + odd(n); }
        unsigned floor2(unsigned n) const { return n/2; }
        unsigned power2(unsigned n) const { SASSERT(n < 10); return 1 << n; }


        literal mk_max(literal a, literal b) {
            if (a == b) return a;
            m_stats.m_num_compiled_vars++;
            return ctx.mk_max(a, b);
        }

        literal mk_min(literal a, literal b) {
            if (a == b) return a;
            m_stats.m_num_compiled_vars++;
            return ctx.mk_min(a, b);
        }

        literal fresh() {
            m_stats.m_num_compiled_vars++;
            return ctx.fresh();
        }
        void add_clause(literal l1, literal l2, literal l3) {
            literal lits[3] = { l1, l2, l3 };
            add_clause(3, lits);
        }
        void add_clause(literal l1, literal l2) {
            literal lits[2] = { l1, l2 };
            add_clause(2, lits);
        }
        void add_clause(literal_vector const& lits) {
            add_clause(lits.size(), lits.c_ptr());
        }
        void add_clause(unsigned n, literal const* ls) {
            m_stats.m_num_compiled_clauses++;
            m_stats.m_num_clause_vars += n;
            literal_vector tmp(n, ls);
            TRACE("pb", for (unsigned i = 0; i < n; ++i) tout << ls[i] << " "; tout << "\n";);
            ctx.mk_clause(n, tmp.c_ptr());
        }

        // y1 <= mk_max(x1,x2)
        // y2 <= mk_min(x1,x2)
        void cmp_ge(literal x1, literal x2, literal y1, literal y2) {
            add_clause(ctx.mk_not(y2), x1);
            add_clause(ctx.mk_not(y2), x2);
            add_clause(ctx.mk_not(y1), x1, x2);            
        }

        // mk_max(x1,x2) <= y1
        // mk_min(x1,x2) <= y2
        void cmp_le(literal x1, literal x2, literal y1, literal y2) {
            add_clause(ctx.mk_not(x1), y1);
            add_clause(ctx.mk_not(x2), y1);
            add_clause(ctx.mk_not(x1), ctx.mk_not(x2), y2);
        }

        void cmp_eq(literal x1, literal x2, literal y1, literal y2) {
            cmp_ge(x1, x2, y1, y2);
            cmp_le(x1, x2, y1, y2);
        }

        void cmp(literal x1, literal x2, literal y1, literal y2) {
            switch(m_t) {
            case LE: case LE_FULL: cmp_le(x1, x2, y1, y2); break;
            case GE: case GE_FULL: cmp_ge(x1, x2, y1, y2); break;
            case EQ: cmp_eq(x1, x2, y1, y2); break;
            }
        }
        vc vc_cmp() {
            return vc(2, (m_t==EQ)?6:3);
        }

        void card(unsigned k, unsigned n, literal const* xs, literal_vector& out) {
            TRACE("pb", tout << "card k: " << k << " n: " << n << "\n";);
            if (n <= k) {
                psort_nw<psort_expr>::sorting(n, xs, out);
            }
            else if (use_dcard(k, n)) {
                dsorting(k, n, xs, out);
            }
            else {
                literal_vector out1, out2;
                unsigned l = n/2; // TBD
                card(k, l, xs, out1);
                card(k, n-l, xs + l, out2);
                smerge(k, out1.size(), out1.c_ptr(), out2.size(), out2.c_ptr(), out);
            }
            TRACE("pb", tout << "card k: " << k << " n: " << n << "\n";
                  pp(tout << "in:", n, xs) << "\n";
                  pp(tout << "out:", out) << "\n";);

        }        
        vc vc_card(unsigned k, unsigned n) {
            if (n <= k) {
                return vc_sorting(n);
            }
            else if (use_dcard(k, n)) {
                return vc_dsorting(k, n);
            }
            else {
                return vc_card_rec(k, n);
            }
        }
        vc vc_card_rec(unsigned k, unsigned n) {
            unsigned l = n/2;
            return vc_card(k, l) + vc_card(k, n-l) + vc_smerge(k, l, n-l);
        }
        bool use_dcard(unsigned k, unsigned n) {
            return m_force_dcard || (!m_disable_dcard && n < 10 && vc_dsorting(k, n) < vc_card_rec(k, n));
        }


        void merge(unsigned a, literal const* as, 
                   unsigned b, literal const* bs,                    
                   literal_vector& out) {
            TRACE("pb", tout << "merge a: " << a << " b: " << b << "\n";);
            if (a == 1 && b == 1) {
                literal y1 = mk_max(as[0], bs[0]);
                literal y2 = mk_min(as[0], bs[0]);
                out.push_back(y1);
                out.push_back(y2);
                psort_nw<psort_expr>::cmp(as[0], bs[0], y1, y2);
            }
            else if (a == 0) {
                out.append(b, bs);
            }
            else if (b == 0) {
                out.append(a, as);
            }
            else if (use_dsmerge(a, b, a + b)) {
                dsmerge(a + b, a, as, b, bs, out);
            }
            else if (even(a) && odd(b)) {
                merge(b, bs, a, as, out);                
            }
            else {
                literal_vector even_a, odd_a;
                literal_vector even_b, odd_b;
                literal_vector out1, out2;
                SASSERT(a > 1 || b > 1);
                split(a, as, even_a, odd_a);
                split(b, bs, even_b, odd_b);
                SASSERT(!even_a.empty());
                SASSERT(!even_b.empty());
                merge(even_a.size(), even_a.c_ptr(),
                      even_b.size(), even_b.c_ptr(), out1);
                merge(odd_a.size(), odd_a.c_ptr(),
                      odd_b.size(), odd_b.c_ptr(), out2);
                interleave(out1, out2, out); 
            }
            TRACE("pb", tout << "merge a: " << a << " b: " << b << "\n";
                  pp(tout << "a:", a, as) << "\n";
                  pp(tout << "b:", b, bs) << "\n";
                  pp(tout << "out:", out) << "\n";);
        }
        vc vc_merge(unsigned a, unsigned b) {
            if (a == 1 && b == 1) {
                return vc_cmp();
            }
            else if (a == 0 || b == 0) {
                return vc(0, 0);
            }
            else if (use_dsmerge(a, b, a + b)) {
                return vc_dsmerge(a, b, a + b);
            }
            else {
                return vc_merge_rec(a, b);
            }
        }
        vc vc_merge_rec(unsigned a, unsigned b) {
            return 
                vc_merge(ceil2(a),  ceil2(b)) +
                vc_merge(floor2(a), floor2(b)) +
                vc_interleave(ceil2(a) + ceil2(b), floor2(a) + floor2(b));
        }
        void split(unsigned n, literal const* ls, literal_vector& even, literal_vector& odd) {
            for (unsigned i = 0; i < n; i += 2) {
                even.push_back(ls[i]);
            }
            for (unsigned i = 1; i < n; i += 2) {
                odd.push_back(ls[i]);
            }
        }

        void interleave(literal_vector const& as, 
                        literal_vector const& bs,
                        literal_vector& out) {
            TRACE("pb", tout << "interleave: " << as.size() << " " << bs.size() << "\n";);
            SASSERT(as.size() >= bs.size());
            SASSERT(as.size() <= bs.size() + 2);
            SASSERT(!as.empty());
            out.push_back(as[0]);
            unsigned sz = std::min(as.size()-1, bs.size());
            for (unsigned i = 0; i < sz; ++i) {
                literal y1 = mk_max(as[i+1],bs[i]);
                literal y2 = mk_min(as[i+1],bs[i]);
                psort_nw<psort_expr>::cmp(as[i+1], bs[i], y1, y2);
                out.push_back(y1);
                out.push_back(y2);
            }            
            if (as.size() == bs.size()) {
                out.push_back(bs[sz]);
            }
            else if (as.size() == bs.size() + 2) {
                out.push_back(as[sz+1]);
            }
            SASSERT(out.size() == as.size() + bs.size());
            TRACE("pb", tout << "interleave: " << as.size() << " " << bs.size() << "\n";
                  pp(tout << "a: ", as) << "\n";
                  pp(tout << "b: ", bs) << "\n";
                  pp(tout << "out: ", out) << "\n";);

        }
        vc vc_interleave(unsigned a, unsigned b) {
            return vc_cmp()*std::min(a-1,b);
        }
        
    public:
        void sorting(unsigned n, literal const* xs, literal_vector& out) {
            TRACE("pb", tout << "sorting: " << n << "\n";);
            switch(n) {
            case 0: 
                break;
            case 1: 
                out.push_back(xs[0]); 
                break;
            case 2: 
                psort_nw<psort_expr>::merge(1, xs, 1, xs+1, out); 
                break;
            default:
                if (use_dsorting(n)) {
                    dsorting(n, n, xs, out);
                }
                else {
                    literal_vector out1, out2;
                    unsigned l = n/2;  // TBD
                    sorting(l, xs, out1);
                    sorting(n-l, xs+l, out2);
                    merge(out1.size(), out1.c_ptr(), 
                          out2.size(), out2.c_ptr(),
                          out);                
                }
                break;
            }
            TRACE("pb", tout << "sorting: " << n << "\n";
                  pp(tout << "in:", n, xs) << "\n"; 
                  pp(tout << "out:", out) << "\n";);
        }

    private:
        vc vc_sorting(unsigned n) {
            switch(n) {
            case 0: return vc(0,0);
            case 1: return vc(0,0);
            case 2: return vc_merge(1,1);
            default:
                if (use_dsorting(n)) {
                    return vc_dsorting(n, n);
                }
                else {
                    return vc_sorting_rec(n);
                }
            }
        }
        vc vc_sorting_rec(unsigned n) {
            SASSERT(n > 2);
            unsigned l = n/2;
            return vc_sorting(l) + vc_sorting(n-l) + vc_merge(l, n-l);
        }

        bool use_dsorting(unsigned n) {
            SASSERT(n > 2);            
            return m_force_dsorting || 
                (!m_disable_dsorting && n < 10 && vc_dsorting(n, n) < vc_sorting_rec(n));
        }

        void smerge(unsigned c,
                    unsigned a, literal const* as,
                    unsigned b, literal const* bs, 
                    literal_vector& out) {
            TRACE("pb", tout << "smerge: c:" << c << " a:" << a << " b:" << b << "\n";);
            if (a == 1 && b == 1 && c == 1) {
                literal y = mk_max(as[0], bs[0]);
                if (m_t != GE) {
                    // x1 <= mk_max(x1,x2)
                    // x2 <= mk_max(x1,x2)
                    add_clause(ctx.mk_not(as[0]), y);
                    add_clause(ctx.mk_not(bs[0]), y);
                }
                if (m_t != LE) {
                    // mk_max(x1,x2) <= x1, x2
                    add_clause(ctx.mk_not(y), as[0], bs[0]);
                }
                out.push_back(y);
            }
            else if (a == 0) {
                out.append(std::min(c, b), bs);
            }
            else if (b == 0) {
                out.append(std::min(c, a), as);
            }
            else if (a > c) {
                smerge(c, c, as, b, bs, out);
            }
            else if (b > c) {
                smerge(c, a, as, c, bs, out);
            }
            else if (a + b <= c) {
                merge(a, as, b, bs, out);
            }
            else if (use_dsmerge(a, b, c)) {
                dsmerge(c, a, as, b, bs, out);
            }
            else {
                literal_vector even_a, odd_a;
                literal_vector even_b, odd_b;
                literal_vector out1, out2;               
                split(a, as, even_a, odd_a);
                split(b, bs, even_b, odd_b);
                SASSERT(!even_a.empty());
                SASSERT(!even_b.empty());
                unsigned c1, c2;
                if (even(c)) {
                    c1 = 1 + c/2; c2 = c/2;
                }
                else {
                    c1 = (c + 1)/2; c2 = (c - 1)/2;
                }
                smerge(c1, even_a.size(), even_a.c_ptr(),
                       even_b.size(), even_b.c_ptr(), out1);
                smerge(c2, odd_a.size(), odd_a.c_ptr(),
                       odd_b.size(), odd_b.c_ptr(), out2);
                SASSERT(out1.size() == std::min(even_a.size()+even_b.size(), c1));
                SASSERT(out2.size() == std::min(odd_a.size()+odd_b.size(), c2));
                literal y;
                if (even(c)) {
                    literal z1 = out1.back();
                    literal z2 = out2.back();
                    out1.pop_back();
                    out2.pop_back();
                    y = mk_max(z1, z2);
                    if (m_t != GE) {
                        add_clause(ctx.mk_not(z1), y);
                        add_clause(ctx.mk_not(z2), y);
                    }
                    if (m_t != LE) {
                        add_clause(ctx.mk_not(y), z1, z2);
                    }
                }
                interleave(out1, out2, out);                 
                if (even(c)) {
                    out.push_back(y);
                }
            }
            TRACE("pb", tout << "smerge: c:" << c << " a:" << a << " b:" << b << "\n";
                  pp(tout << "a:", a, as) << "\n";
                  pp(tout << "b:", b, bs) << "\n";
                  pp(tout << "out:", out) << "\n";
                  );
            SASSERT(out.size() == std::min(a + b, c));
        }

        vc vc_smerge(unsigned a, unsigned b, unsigned c) {
            if (a == 1 && b == 1 && c == 1) {
                vc v(1,0);
                if (m_t != GE) v = v + vc(0, 2);
                if (m_t != LE) v = v + vc(0, 1);
                return v;
            }
            if (a == 0 || b == 0) return vc(0, 0);
            if (a > c) return vc_smerge(c, b, c);
            if (b > c) return vc_smerge(a, c, c);
            if (a + b <= c) return vc_merge(a, b);
            if (use_dsmerge(a, b, c)) return vc_dsmerge(a, b, c);
            return vc_smerge_rec(a, b, c);
        }
        vc vc_smerge_rec(unsigned a, unsigned b, unsigned c) {
            return 
                vc_smerge(ceil2(a), ceil2(b), even(c)?(1+c/2):((c+1)/2)) +
                vc_smerge(floor2(a), floor2(b), even(c)?(c/2):((c-1)/2)) +
                vc_interleave(ceil2(a)+ceil2(b),floor2(a)+floor2(b)) +
                vc(1, 0) +
                ((m_t != GE)?vc(0, 2):vc(0, 0)) +
                ((m_t != LE)?vc(0, 1):vc(0, 0));
        }
        bool use_dsmerge(unsigned a, unsigned b, unsigned c) {
            return 
                m_force_dsmerge ||
                (!m_disable_dsmerge && 
                 a < (1 << 15) && b < (1 << 15) && 
                 vc_dsmerge(a, b, a + b) < vc_smerge_rec(a, b, c));
        }

        void dsmerge(            
            unsigned c,
            unsigned a, literal const* as, 
            unsigned b, literal const* bs,                    
            literal_vector& out) {
            TRACE("pb", tout << "dsmerge: c:" << c << " a:" << a << " b:" << b << "\n";);
            SASSERT(a <= c);
            SASSERT(b <= c);
            SASSERT(a + b >= c);
            for (unsigned i = 0; i < c; ++i) {
                out.push_back(fresh());
            }
            if (m_t != GE) {
                for (unsigned i = 0; i < a; ++i) {
                    add_clause(ctx.mk_not(as[i]), out[i]);
                }
                for (unsigned i = 0; i < b; ++i) {
                    add_clause(ctx.mk_not(bs[i]), out[i]);
                }
                for (unsigned i = 1; i <= a; ++i) {
                    for (unsigned j = 1; j <= b && i + j <= c; ++j) {
                        add_clause(ctx.mk_not(as[i-1]),ctx.mk_not(bs[j-1]),out[i+j-1]);
                    }
                }
            }
            if (m_t != LE) {
                literal_vector ls;
                for (unsigned k = 0; k < c; ++k) {
                    ls.reset();
                    ls.push_back(ctx.mk_not(out[k]));
                    if (a <= k) {
                        add_clause(ctx.mk_not(out[k]), bs[k-a]);
                    }
                    if (b <= k) {
                        add_clause(ctx.mk_not(out[k]), as[k-b]);
                    }
                    for (unsigned i = 0; i < std::min(a,k + 1); ++i) {
                        unsigned j = k - i;
                        SASSERT(i + j == k);
                        if (j < b) {
                            ls.push_back(as[i]);
                            ls.push_back(bs[j]);
                            add_clause(ls);
                            ls.pop_back();
                            ls.pop_back();
                        }
                    }
                }
            }
        }
        vc vc_dsmerge(unsigned a, unsigned b, unsigned c) {
            vc v(c, 0);
            if (m_t != GE) {
                v = v + vc(0, a + b + std::min(a, c)*std::min(b, c)/2);
            }
            if (m_t != LE) {
                v = v + vc(0, std::min(a, c)*std::min(b, c)/2);
            }
            return v;
        }


        void dsorting(unsigned m, unsigned n, literal const* xs, 
                      literal_vector& out) {
            TRACE("pb", tout << "dsorting m: " << m << " n: " << n << "\n";);
            SASSERT(m <= n);
            literal_vector lits;
            for (unsigned i = 0; i < m; ++i) {
                out.push_back(fresh());
            }
            if (m_t != GE) {
                for (unsigned k = 1; k <= m; ++k) {
                    lits.push_back(out[k-1]);
                    add_subset(true, k, 0, lits, n, xs);
                    lits.pop_back();
                }
            }
            if (m_t != LE) {                
                for (unsigned k = 1; k <= m; ++k) {
                    lits.push_back(ctx.mk_not(out[k-1]));
                    add_subset(false, n-k+1, 0, lits, n, xs);
                    lits.pop_back();
                }
            }
        }
        vc vc_dsorting(unsigned m, unsigned n) {
            SASSERT(m <= n && n < 10);            
            vc v(m, 0);
            if (m_t != GE) {
                v = v + vc(0, power2(n-1));
            }
            if (m_t != LE) {
                v = v + vc(0, power2(n-1));
            }
            return v;
        }

        void add_subset(bool polarity, unsigned k, unsigned offset, literal_vector& lits, 
                        unsigned n, literal const* xs) {
            TRACE("pb", tout << "k:" << k << " offset: " << offset << " n: " << n << " ";
                  pp(tout, lits) << "\n";);
            SASSERT(k + offset <= n);
            if (k == 0) {
                add_clause(lits);
                return;
            }
            for (unsigned i = offset; i < n - k + 1; ++i) {
                lits.push_back(polarity?ctx.mk_not(xs[i]):xs[i]);
                add_subset(polarity, k-1, i+1, lits, n, xs);
                lits.pop_back();
            }
        }
    };

#endif
