/*++
Copyright (c) 2013 Microsoft Corporation

Module Name:

    elim01_tactic.h

Abstract:

    Replace 0-1 integer variables by Booleans.

Author:

    Nikolaj Bjorner (nbjorner) 2013-12-7

Notes:

--*/
#ifndef ELIM01_TACTIC_H_
#define ELIM01_TACTIC_H_

#include "util/params.h"
class ast_manager;
class tactic;

tactic * mk_elim01_tactic(ast_manager & m, params_ref const & p = params_ref());

/*
    ADD_TACTIC("elim01", "eliminate 0-1 integer variables, replace them by Booleans.", "mk_elim01_tactic(m, p)")
*/


#endif
