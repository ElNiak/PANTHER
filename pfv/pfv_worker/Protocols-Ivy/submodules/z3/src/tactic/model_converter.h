/*++
Copyright (c) 2011 Microsoft Corporation

Module Name:

    model_converter.h

Abstract:

    Abstract interface for converting models.

Author:

    Leonardo (leonardo) 2011-04-21

Notes:

--*/
#ifndef MODEL_CONVERTER_H_
#define MODEL_CONVERTER_H_

#include "model/model.h"
#include "tactic/converter.h"
#include "util/ref.h"

class labels_vec : public svector<symbol> {};

class model_converter : public converter {
public:
    virtual void operator()(model_ref & m) {}  // TODO: delete

    virtual void operator()(model_ref & m, unsigned goal_idx) {
        // TODO: make it virtual after the transition to goal/tactic/tactical is complete
        SASSERT(goal_idx == 0);
        operator()(m);
    }

    virtual void operator()(labels_vec & r, unsigned goal_idx) {}
    
    virtual model_converter * translate(ast_translation & translator) = 0;
};

typedef ref<model_converter> model_converter_ref;

model_converter * concat(model_converter * mc1, model_converter * mc2);

/**
   \brief \c mc1 is the model converter for a sequence of subgoals of size \c num.
   Given an i in [0, num), mc2s[i] is the model converter for subgoal i,
   and num_subgoals[i] is the number of subgoals of subgoals[i].
*/
model_converter * concat(model_converter * mc1, unsigned num, model_converter * const * mc2s, unsigned * num_subgoals);

model_converter * model2model_converter(model * m);

model_converter * model_and_labels2model_converter(model * m, buffer<symbol> &r);

void model_converter2model(ast_manager & mng, model_converter * mc, model_ref & m);

void apply(model_converter_ref & mc, model_ref & m, unsigned gidx);

typedef sref_vector<model_converter> model_converter_ref_vector;
typedef sref_buffer<model_converter> model_converter_ref_buffer;

#endif
