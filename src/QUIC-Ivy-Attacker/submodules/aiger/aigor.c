/***************************************************************************
Copyright (c) 2009-2011, Armin Biere, Johannes Kepler University.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to
deal in the Software without restriction, including without limitation the
rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
sell copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
IN THE SOFTWARE.
***************************************************************************/

#include "aiger.h"

#include <assert.h>
#include <stdarg.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#define USAGE \
"usage: aigor [-h][-v][<input> [<output>]]\n" \
"\n" \
"Disjunction of all outputs of an AIGER model.\n"

static aiger * src, * dst;
static int verbose = 0;

static void
die (const char *fmt, ...)
{
  va_list ap;
  fputs ("*** [aigor] ", stderr);
  va_start (ap, fmt);
  vfprintf (stderr, fmt, ap);
  va_end (ap);
  fputc ('\n', stderr);
  fflush (stderr);
  exit (1);
}

static void
msg (const char *fmt, ...)
{
  va_list ap;
  if (!verbose)
    return;
  fputs ("[aigor] ", stderr);
  va_start (ap, fmt);
  vfprintf (stderr, fmt, ap);
  va_end (ap);
  fputc ('\n', stderr);
  fflush (stderr);
}

int
main (int argc, char ** argv)
{
  const char * input, * output, * err;
  unsigned j, out, tmp;
  char comment[80];
  aiger_mode mode;
  aiger_and * a;
  int i, ok;

  input = output = 0;

  for (i = 1; i < argc; i++)
    {
      if (!strcmp (argv[i], "-h"))
	{
	  printf ("%s", USAGE);
	  exit (0);
	}

      if (!strcmp (argv[i], "-v"))
	verbose = 1;
      else if (argv[i][0] == '-')
	die ("invalid command line option '%s'", argv[i]);
      else if (output)
	die ("too many arguments");
      else if (input)
	output = argv[i];
      else
	input = argv[i];
    }

  msg ("reading %s", input ? input : "<stdin>");
  src = aiger_init ();
  if (input)
    err = aiger_open_and_read_from_file (src, input);
  else
    err = aiger_read_from_file (src, stdin);

  if (err)
    die ("read error: %s", err);

  msg ("read MILOA %u %u %u %u %u", 
       src->maxvar,
       src->num_inputs,
       src->num_latches,
       src->num_outputs,
       src->num_ands);

  dst = aiger_init ();
  for (j = 0; j < src->num_inputs; j++)
    aiger_add_input (dst, src->inputs[j].lit, src->inputs[j].name);

  for (j = 0; j < src->num_latches; j++) {
    aiger_add_latch (dst, src->latches[j].lit, 
                          src->latches[j].next,
                          src->latches[j].name);
    aiger_add_reset (dst, src->latches[j].lit, 
                          src->latches[j].reset);
  }

  for (j = 0; j < src->num_ands; j++)
    {
      a = src->ands + j;
      aiger_add_and (dst, a->lhs, a->rhs0, a->rhs1);
    }

  if (src->num_outputs)
    {
      out = src->outputs[0].lit;
      for (j = 1; j < src->num_outputs; j++)
	{
          tmp = 2 * (dst->maxvar + 1);
	  aiger_add_and (dst, tmp, out, aiger_not (src->outputs[j].lit));
	  out = tmp;
	}
      aiger_add_output (dst, aiger_not (out), "AIGER_OR");
    }

  sprintf (comment, "aigor");
  aiger_add_comment (dst, comment);
  sprintf (comment, "disjunction of %u original outputs", src->num_outputs);
  aiger_add_comment (dst, comment);

  aiger_reset (src);

  msg ("writing %s", output ? output : "<stdout>");

  if (output)
    ok = aiger_open_and_write_to_file (dst, output);
  else
    {
      mode = isatty (1) ? aiger_ascii_mode : aiger_binary_mode;
      ok = aiger_write_to_file (dst, mode, stdout);
    }

  if (!ok)
    die ("writing failed");

  msg ("wrote MILOA %u %u %u %u %u", 
       dst->maxvar,
       dst->num_inputs,
       dst->num_latches,
       dst->num_outputs,
       dst->num_ands);

  aiger_reset (dst);

  return 0;
}
